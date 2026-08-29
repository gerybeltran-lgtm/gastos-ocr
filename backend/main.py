import os
# Cargar variables de entorno desde .env antes de cualquier otra importación
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv no instalado, se usarán variables del sistema

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import shutil
import uuid
from pydantic import BaseModel
from supabase import create_client, Client
import fitz  # PyMuPDF

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Constantes de seguridad ---
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}

ADMIN_EMAILS = ["gerardo.beltran@e-voltage.cl", "jose.diaz@e-voltage.cl", "jorge.salas@e-voltage.cl"]
APPROVER_EMAILS = ["gerardo.beltran@e-voltage.cl", "jose.diaz@e-voltage.cl"]

def send_notification_email(data: dict):
    sender_email = os.environ.get("SENDER_EMAIL", "notificacionesevoltage@gmail.com")
    app_password = os.environ.get("EMAIL_PASSWORD", "")
    receiver_emails = ADMIN_EMAILS

    subject = f"Nueva Rendición: {data.get('tipo_transaccion', 'Desconocido')} de {data.get('usuario_nombre', 'Usuario')}"
    
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #38bdf8; padding: 20px; text-align: center; color: white;">
                <h2 style="margin: 0;">Nueva Transacción Registrada</h2>
            </div>
            <div style="padding: 30px; background-color: #f8fafc;">
                <p><strong>Usuario:</strong> {data.get('usuario_nombre')}</p>
                <p><strong>Tipo:</strong> {data.get('tipo_transaccion')} (Estado: Pendiente)</p>
                <p><strong>Monto:</strong> ${float(data.get('monto_total', 0)):,.0f}</p>
                <p><strong>Centro de Costo:</strong> {data.get('centro_costo', '-')}</p>
                <p><strong>Proveedor:</strong> {data.get('rut_proveedor', '-')}</p>
                <p><strong>Fecha:</strong> {data.get('fecha_boleta', '-')}</p>
                <p><strong>Motivo / Descripción:</strong> {data.get('descripcion', '-')}</p>
                <br>
                <a href="{data.get('link_drive', '#')}" style="display: inline-block; padding: 12px 24px; background-color: #10b981; color: white; text-decoration: none; border-radius: 6px; font-weight: bold;">Ver Documento Respaldo</a>
                <br><br>
                <p style="font-size: 12px; color: #64748b;">Para aprobar o rechazar esta solicitud, ingrese al Panel de Administrador en la plataforma DealFlow Gastos.</p>
            </div>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"E-Voltage Notificaciones <{sender_email}>"
    msg["To"] = ", ".join(receiver_emails)
    
    part = MIMEText(html_content, "html")
    msg.attach(part)
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_emails, msg.as_string())
        server.quit()
        print("Correo enviado exitosamente a los administradores.")
    except Exception as e:
        print(f"Error enviando correo: {str(e)}")

# Configurar credenciales de Google antes de importar el procesador
import json

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
cred_path = os.path.join(BASE_DIR, 'credentials.json')

# Si estamos en Render u otra nube, podemos pasar el JSON como string en una variable de entorno
if os.environ.get("GOOGLE_CREDENTIALS_JSON"):
    try:
        creds_data = json.loads(os.environ.get("GOOGLE_CREDENTIALS_JSON"))
        if "private_key" in creds_data:
            creds_data["private_key"] = creds_data["private_key"].replace('\\n', '\n')
        with open(cred_path, "w") as f:
            json.dump(creds_data, f)
    except Exception as e:
        print("Error al escribir credentials.json:", e)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path

# Supabase CRM Config — leído desde variables de entorno
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("ERROR: Faltan variables de entorno SUPABASE_URL o SUPABASE_KEY. Configura el archivo .env")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

from procesador_gastos import preprocess_image, extract_text_from_image, parse_receipt_data
from google_services import upload_image_to_drive, overwrite_sheets
from typing import List, Optional

app = FastAPI(title="API Rendición de Gastos")

_allowed_origins_raw = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,https://gastos-ocr.vercel.app")
origins = [origin.strip() for origin in _allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SaveReceiptPayload(BaseModel):
    id: str
    usuario_nombre: str
    usuario_email: str
    departamento: str
    centro_costo: str
    rut_proveedor: Optional[str] = None
    fecha_boleta: Optional[str] = None
    monto_total: float
    iva: float
    link_drive: Optional[str] = None
    tipo_transaccion: Optional[str] = "Boleta"
    origen_fondos: Optional[str] = "Caja Principal"
    monto_caja: Optional[float] = 0.0
    monto_nc: Optional[float] = 0.0
    clasificacion_sin_respaldo: Optional[str] = None
    estado: Optional[str] = "Pendiente de Revisión"
    factura_asociada: Optional[str] = None
    comentarios_revisor: Optional[str] = None
    descripcion: Optional[str] = None

class EditExpensePayload(BaseModel):
    departamento: str
    centro_costo: str
    rut_proveedor: Optional[str] = None
    fecha_boleta: Optional[str] = None
    monto_total: float
    link_drive: Optional[str] = None
    tipo_transaccion: Optional[str] = "Boleta"
    origen_fondos: Optional[str] = "Caja Principal"
    monto_caja: Optional[float] = 0.0
    monto_nc: Optional[float] = 0.0
    clasificacion_sin_respaldo: Optional[str] = None
    estado: Optional[str] = "Pendiente de Revisión"
    factura_asociada: Optional[str] = None
    comentarios_revisor: Optional[str] = None
    descripcion: Optional[str] = None

class UpdateStatusPayload(BaseModel):
    id: str
    estado: str
    comentarios_revisor: Optional[str] = None

class ExportPayload(BaseModel):
    rows: list

@app.post("/upload-receipt")
async def upload_receipt(
    file: UploadFile = File(...),
    userName: str = Form(...),
    userEmail: str = Form(...),
    department: str = Form(...),
    costCenter: str = Form(...),
    skip_ocr: Optional[str] = Form(None)
):
    try:
        filename = file.filename or ""
        ext = os.path.splitext(filename)[1].lower()

        # 1. Validación de extensión permitida
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Formato no permitido ({ext}). Solo se aceptan: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # 2. Validación de Content-Type MIME
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo MIME no válido ({file.content_type}). Solo se aceptan imágenes JPEG/PNG y PDFs."
            )

        # 3. Validación de tamaño (guardando en chunks para no saturar memoria)
        transaccion_id = str(uuid.uuid4())
        file_location = f"temp_{transaccion_id}{ext}"
        bytes_written = 0

        with open(file_location, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB por chunk
                bytes_written += len(chunk)
                if bytes_written > MAX_FILE_SIZE_BYTES:
                    buffer.close()
                    if os.path.exists(file_location):
                        os.remove(file_location)
                    raise HTTPException(
                        status_code=400,
                        detail=f"El archivo supera el tamaño máximo de {MAX_FILE_SIZE_MB}MB."
                    )
                buffer.write(chunk)

        try:
            # 1. Subir a Google Drive
            print(f"Subiendo a Google Drive: {file.filename}...")
            link_drive = upload_image_to_drive(file_location, f"{transaccion_id}_{file.filename}")
            print(f"Enlace de Drive: {link_drive}")
            
            extracted_data = {}
            if skip_ocr == "true":
                print("Modo skip_ocr activado: omitiendo procesamiento OCR...")
                extracted_data = {
                    "rut_proveedor": "",
                    "fecha_boleta": datetime.now().strftime("%Y-%m-%d"),
                    "monto_total": 0,
                    "iva": 0
                }
            else:
                # 2. Procesar OCR
                print("Procesando OCR...")
                image_to_process = file_location
                is_pdf = file_location.lower().endswith('.pdf')

                if is_pdf:
                    print("Convirtiendo primera página de PDF a imagen...")
                    pdf_doc = fitz.open(file_location)
                    page = pdf_doc.load_page(0)
                    pix = page.get_pixmap(dpi=150)
                    image_to_process = f"temp_{transaccion_id}_page0.png"
                    pix.save(image_to_process)
                    pdf_doc.close()

                try:
                    processed_img = preprocess_image(image_to_process)
                    text = extract_text_from_image(processed_img)
                    print(f"Texto detectado ({len(text)} caracteres): {text[:100]}...")
                    extracted_data = parse_receipt_data(text)
                finally:
                    if is_pdf and os.path.exists(image_to_process):
                        os.remove(image_to_process)
            
            # Formatear fecha
            fecha_boleta = extracted_data.get("fecha")
            if fecha_boleta:
                try:
                    if "/" in fecha_boleta:
                        parts = fecha_boleta.split("/")
                        if len(parts) == 3:
                            if len(parts[0]) == 4:
                                fecha_boleta = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                            else:
                                fecha_boleta = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                    elif "-" in fecha_boleta:
                        parts = fecha_boleta.split("-")
                        if len(parts) == 3:
                            if len(parts[0]) != 4:
                                fecha_boleta = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                except Exception as e:
                    print("Error formateando fecha:", e)

            # Estructurar respuesta para la revisión
            response_data = {
                "id": transaccion_id,
                "usuario_nombre": userName,
                "usuario_email": userEmail,
                "departamento": department,
                "centro_costo": costCenter,
                "rut_proveedor": extracted_data.get("rut"),
                "fecha_boleta": fecha_boleta,
                "monto_total": extracted_data.get("total", 0),
                "iva": extracted_data.get("iva", 0),
                "link_drive": link_drive
            }
            
            return {
                "success": True,
                "message": "Boleta procesada exitosamente",
                "data": response_data
            }
            
        finally:
            if os.path.exists(file_location):
                os.remove(file_location)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        err_msg = str(e)
        print(f"Error procesando boleta: {err_msg}")
        traceback.print_exc()
        # Fallback estructurado en caso de error de OCR / API
        return {
            "success": False,
            "error": f"Error del servidor de IA: {err_msg}",
            "data": {
                "id": str(uuid.uuid4()) if 'uuid' in locals() else "temp-id",
                "usuario_nombre": userName,
                "usuario_email": userEmail,
                "departamento": department,
                "centro_costo": costCenter,
                "rut_proveedor": None,
                "fecha_boleta": datetime.now().strftime("%Y-%m-%d"),
                "monto_total": 0,
                "iva": 0,
                "link_drive": link_drive if 'link_drive' in locals() else None
            }
        }

@app.post("/save-receipt")
async def save_receipt(data: SaveReceiptPayload, background_tasks: BackgroundTasks):
    try:
        fecha_captura = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Validar y normalizar Ledger Segregado (Bolsas contables)
        final_origen = data.origen_fondos or "Caja Principal"
        final_monto_caja = float(data.monto_caja or 0)
        final_monto_nc = float(data.monto_nc or 0)
        final_monto_total = float(data.monto_total or 0)

        if final_origen == "Fondos Mixtos":
            if abs((final_monto_caja + final_monto_nc) - final_monto_total) > 0.01:
                raise HTTPException(
                    status_code=400, 
                    detail=f"La suma de Monto Caja (${final_monto_caja:,.0f}) y Monto NC (${final_monto_nc:,.0f}) debe coincidir exactamente con el Monto Total (${final_monto_total:,.0f})"
                )
        elif final_origen == "Casa Comercial":
            final_monto_caja = 0.0
            final_monto_nc = final_monto_total
        elif data.tipo_transaccion == "Sin Respaldo" or final_origen == "Cuentas por Recuperar":
            final_origen = "Cuentas por Recuperar"
            final_monto_caja = final_monto_total
            final_monto_nc = 0.0
        else:
            final_origen = "Caja Principal"
            final_monto_caja = final_monto_total
            final_monto_nc = 0.0

        # Guardar en Supabase (CRM)
        supabase_data = {
            "id": data.id,
            "usuario_nombre": data.usuario_nombre,
            "usuario_email": data.usuario_email,
            "departamento": data.departamento,
            "centro_costo": data.centro_costo,
            "rut_proveedor": data.rut_proveedor,
            "fecha_boleta": data.fecha_boleta if data.fecha_boleta else None,
            "monto_total": final_monto_total,
            "iva": data.iva,
            "link_drive": data.link_drive,
            "fecha_captura": fecha_captura,
            "tipo_transaccion": data.tipo_transaccion,
            "origen_fondos": final_origen,
            "monto_caja": final_monto_caja,
            "monto_nc": final_monto_nc,
            "clasificacion_sin_respaldo": data.clasificacion_sin_respaldo,
            "estado": data.estado or "Pendiente de Revisión",
            "factura_asociada": data.factura_asociada,
            "comentarios_revisor": data.comentarios_revisor,
            "descripcion": data.descripcion
        }
        supabase.table("transacciones").insert(supabase_data).execute()
        
        # Agregar el envío de correo como tarea en segundo plano
        background_tasks.add_task(send_notification_email, supabase_data)
        
        return {"success": True, "data": supabase_data}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error guardando recibo: {str(e)}")
        return {"success": False, "error": "Error interno al guardar el recibo"}

@app.post("/export-sheets")
async def export_sheets(data: ExportPayload):
    try:
        overwrite_sheets(data.rows)
        return {"success": True}
    except Exception as e:
        print(f"Error exportando a Sheets: {str(e)}")
        return {"success": False, "error": "Error interno al exportar a Sheets"}

@app.get("/history")
async def get_history(email: str):
    try:
        # Obtenemos solo los gastos del usuario que consulta
        response = supabase.table("transacciones").select("*").eq("usuario_email", email).order("fecha_captura", desc=True).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"Error obteniendo historial: {str(e)}")
        return {"success": False, "error": "Error interno al obtener historial"}

@app.get("/capital/{email}")
async def get_capital(email: str):
    try:
        response = supabase.table("capital_usuario").select("monto_asignado").eq("usuario_email", email).execute()
        if response.data and len(response.data) > 0:
            return {"success": True, "monto_asignado": response.data[0]["monto_asignado"]}
        return {"success": True, "monto_asignado": 0}
    except Exception as e:
        print(f"Error obteniendo capital: {str(e)}")
        return {"success": False, "error": "Error interno al obtener capital"}

@app.get("/admin/history")
async def admin_history(request: Request, email: str):
    # Verificar que el email venga del header X-User-Email además del query param
    header_email = request.headers.get("X-User-Email", "").lower()
    query_email = email.lower()
    if header_email != query_email or query_email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    try:
        # Obtenemos TODOS los gastos para el panel admin
        response = supabase.table("transacciones").select("*").order("fecha_captura", desc=True).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"Error obteniendo historial admin: {str(e)}")
        return {"success": False, "error": "Error interno al obtener historial admin"}

@app.post("/update-expense-status")
async def update_expense_status(data: UpdateStatusPayload, request: Request):
    try:
        # Verificar permisos de aprobación (Solo Gerardo y José)
        header_email = request.headers.get("X-User-Email", "").lower()
        if not header_email or header_email not in APPROVER_EMAILS:
            raise HTTPException(status_code=403, detail="Solo Gerencia/Finanzas (Gerardo y José) tienen autorización para aprobar o rechazar rendiciones")

        response = supabase.table("transacciones").update({
            "estado": data.estado,
            "comentarios_revisor": data.comentarios_revisor
        }).eq("id", data.id).execute()
        return {"success": True, "data": response.data}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating status: {str(e)}")
        return {"success": False, "error": "Error interno al actualizar estado"}

@app.delete("/expense/{expense_id}")
async def delete_expense(expense_id: str, request: Request):
    try:
        header_email = request.headers.get("X-User-Email", "").lower()
        if not header_email or header_email not in APPROVER_EMAILS:
            raise HTTPException(status_code=403, detail="Solo Gerencia/Finanzas (Gerardo y José) pueden eliminar registros")

        # 1. Eliminar en Supabase
        supabase.table("transacciones").delete().eq("id", expense_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error eliminando gasto: {str(e)}")
        return {"success": False, "error": "Error interno al eliminar el gasto"}

@app.put("/expense/{expense_id}")
async def edit_expense(expense_id: str, data: EditExpensePayload, request: Request):
    try:
        header_email = request.headers.get("X-User-Email", "").lower()
        is_approver = header_email in APPROVER_EMAILS

        # Obtener gasto original de Supabase
        response = supabase.table("transacciones").select("*").eq("id", expense_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Gasto no encontrado")
            
        old_expense = response.data[0]
        
        # Calcular nuevo IVA (desde el Monto Total Bruto)
        nuevo_monto = float(data.monto_total)
        nuevo_iva = round((nuevo_monto * 19) / 119)
        
        # Validar y normalizar Ledger Segregado
        final_origen = data.origen_fondos or old_expense.get("origen_fondos", "Caja Principal")
        final_monto_caja = float(data.monto_caja or 0)
        final_monto_nc = float(data.monto_nc or 0)

        if final_origen == "Fondos Mixtos":
            if abs((final_monto_caja + final_monto_nc) - nuevo_monto) > 0.01:
                raise HTTPException(
                    status_code=400, 
                    detail=f"La suma de Monto Caja (${final_monto_caja:,.0f}) y Monto NC (${final_monto_nc:,.0f}) debe coincidir con el Monto Total (${nuevo_monto:,.0f})"
                )
        elif final_origen == "Casa Comercial":
            final_monto_caja = 0.0
            final_monto_nc = nuevo_monto
        elif data.tipo_transaccion == "Sin Respaldo" or final_origen == "Cuentas por Recuperar":
            final_origen = "Cuentas por Recuperar"
            final_monto_caja = nuevo_monto
            final_monto_nc = 0.0
        else:
            final_origen = "Caja Principal"
            final_monto_caja = nuevo_monto
            final_monto_nc = 0.0

        # Protección RBAC: Solo los aprobadores autorizados pueden cambiar el estado existente
        if is_approver and data.estado:
            final_estado = data.estado
        else:
            final_estado = old_expense.get("estado", "Pendiente de Revisión")

        # Actualizar Supabase
        update_data = {
            "departamento": data.departamento,
            "centro_costo": data.centro_costo,
            "rut_proveedor": data.rut_proveedor,
            "fecha_boleta": data.fecha_boleta if data.fecha_boleta else None,
            "monto_total": nuevo_monto,
            "iva": nuevo_iva,
            "link_drive": data.link_drive if data.link_drive is not None else old_expense.get("link_drive"),
            "tipo_transaccion": data.tipo_transaccion,
            "origen_fondos": final_origen,
            "monto_caja": final_monto_caja,
            "monto_nc": final_monto_nc,
            "clasificacion_sin_respaldo": data.clasificacion_sin_respaldo,
            "estado": final_estado,
            "factura_asociada": data.factura_asociada,
            "comentarios_revisor": data.comentarios_revisor,
            "descripcion": data.descripcion
        }
        supabase.table("transacciones").update(update_data).eq("id", expense_id).execute()
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error editando gasto: {str(e)}")
        return {"success": False, "error": "Error interno al editar el gasto"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
