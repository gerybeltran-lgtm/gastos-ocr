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
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_emails, msg.as_string())
        server.quit()
        print("Correo enviado exitosamente a los administradores.")
    except Exception as e:
        print(f"Error enviando correo: {str(e)}")

# Fin importaciones correo


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

# Supabase CRM Config — leído desde variables de entorno con fallback permanente
DEFAULT_SUPABASE_URL = "https://msfvsjrubvzhkxzqjlhw.supabase.co"
DEFAULT_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1zZnZzanJ1YnZ6aGt4enFqbGh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NDE2NDQyNCwiZXhwIjoyMDc5NzQwNDI0fQ.8xsF4hvpb-Tcul7olI0xdAPXcI0P0SYDqLyrV1i01RU"

SUPABASE_URL = os.environ.get("SUPABASE_URL") or DEFAULT_SUPABASE_URL
_raw_key = os.environ.get("SUPABASE_KEY")
# Si la clave viene vacía o es la clave obsoleta revocada, usar la clave permanente
if not _raw_key or "1HM9jriyskYCDnuQNxNtQg" in _raw_key:
    SUPABASE_KEY = DEFAULT_SERVICE_ROLE_KEY
else:
    SUPABASE_KEY = _raw_key

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
    rut_proveedor: Optional[str] = ""
    fecha_boleta: Optional[str] = None
    monto_total: float
    iva: float
    link_drive: str
    tipo_transaccion: Optional[str] = "Boleta"
    origen_fondos: Optional[str] = "Caja Principal"
    monto_caja: float = 0
    monto_nc: float = 0
    clasificacion_sin_respaldo: Optional[str] = None
    estado: Optional[str] = "Pendiente de Revisión"
    factura_asociada: Optional[str] = ""
    comentarios_revisor: Optional[str] = ""
    descripcion: Optional[str] = ""

class UpdateStatusPayload(BaseModel):
    id: str
    estado: str
    comentarios_revisor: Optional[str] = ""

class ExportSheetsPayload(BaseModel):
    rows: List[List[str]]

class EditExpenseRequest(BaseModel):
    departamento: str
    centro_costo: str
    rut_proveedor: Optional[str] = ""
    fecha_boleta: Optional[str] = None
    monto_total: float
    tipo_transaccion: Optional[str] = "Boleta"
    origen_fondos: Optional[str] = "Caja Principal"
    monto_caja: float = 0
    monto_nc: float = 0
    clasificacion_sin_respaldo: Optional[str] = None
    estado: Optional[str] = "Pendiente de Revisión"
    factura_asociada: Optional[str] = ""
    comentarios_revisor: Optional[str] = ""
    descripcion: Optional[str] = ""
    link_drive: Optional[str] = None


@app.post("/upload-receipt")
async def upload_receipt(
    file: UploadFile = File(...),
    userName: str = Form(...),
    userEmail: str = Form(...),
    department: str = Form(...),
    costCenter: str = Form(...),
    skip_ocr: str = Form("false")
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
                # 2. Convertir PDF a imagen si corresponde
                img_to_process = file_location
                if ext == ".pdf":
                    print("Convirtiendo PDF a imagen para OCR...")
                    doc = fitz.open(file_location)
                    page = doc.load_page(0)  # Primera página
                    pix = page.get_pixmap(dpi=200)
                    img_to_process = f"temp_{transaccion_id}_page0.png"
                    pix.save(img_to_process)
                    doc.close()

                # 3. Preprocesar y extraer datos con Vision API + Regex
                print("Preprocesando imagen para OCR...")
                optimized_path = preprocess_image(img_to_process)
                print("Extrayendo texto con Google Cloud Vision...")
                text = extract_text_from_image(optimized_path)
                print("Analizando datos del comprobante...")
                extracted_data = parse_receipt_data(text)

                # Limpieza de archivo intermedio si fue PDF convertido
                if ext == ".pdf" and os.path.exists(img_to_process):
                    os.remove(img_to_process)
                if os.path.exists(optimized_path) and optimized_path != file_location:
                    os.remove(optimized_path)

            fecha_boleta = extracted_data.get("fecha_boleta") or extracted_data.get("fecha")
            if not fecha_boleta:
                fecha_boleta = datetime.now().strftime("%Y-%m-%d")

            # Estructurar respuesta para la revisión
            rut_prov = extracted_data.get("rut_proveedor") or extracted_data.get("rut") or ""
            rut_rec = extracted_data.get("rut_receptor") or ""
            es_ev = extracted_data.get("es_e_voltage", False)
            total_monto = extracted_data.get("monto_total") or extracted_data.get("total") or 0
            iva_val = extracted_data.get("iva") or (round((total_monto * 19) / 119) if total_monto else 0)

            response_data = {
                "id": transaccion_id,
                "usuario_nombre": userName,
                "usuario_email": userEmail,
                "departamento": department,
                "centro_costo": costCenter,
                "rut_proveedor": rut_prov,
                "rut_receptor": rut_rec,
                "es_e_voltage": es_ev,
                "fecha_boleta": fecha_boleta,
                "monto_total": total_monto,
                "iva": iva_val,
                "link_drive": link_drive
            }

            return {
                "success": True,
                "message": "Archivo procesado exitosamente",
                "data": response_data
            }

        finally:
            # Limpieza del archivo temporal original
            if os.path.exists(file_location):
                os.remove(file_location)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error procesando comprobante: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.post("/save-receipt")
async def save_receipt(payload: SaveReceiptPayload, background_tasks: BackgroundTasks):
    try:
        # Validación de Ledger Segregado (Bolsas contables)
        # Regla: Si origen_fondos es Fondos Mixtos, la suma de caja + nc debe igualar monto_total
        if payload.origen_fondos == "Fondos Mixtos":
            suma_bolsas = (payload.monto_caja or 0) + (payload.monto_nc or 0)
            if abs(suma_bolsas - payload.monto_total) > 1:  # Margen de $1 por redondeo
                raise HTTPException(
                    status_code=400,
                    detail=f"La suma de Monto Caja (${payload.monto_caja:,.0f}) y Monto NC (${payload.monto_nc:,.0f}) debe coincidir exactamente con el Monto Total (${payload.monto_total:,.0f})."
                )
        elif payload.origen_fondos == "Casa Comercial":
            # Si se financió 100% con saldo NC/Casa comercial, no se resta de caja física
            payload.monto_caja = 0
            payload.monto_nc = payload.monto_total
        elif payload.tipo_transaccion == "Sin Respaldo" or payload.origen_fondos == "Cuentas por Recuperar":
            # Todo gasto sin respaldo va a la bolsa de Cuentas por Recuperar
            payload.origen_fondos = "Cuentas por Recuperar"
            payload.monto_caja = payload.monto_total
            payload.monto_nc = 0
        else:
            # Por defecto: Caja Principal asume el monto completo
            payload.monto_caja = payload.monto_total
            payload.monto_nc = 0

        fecha_captura = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fecha_boleta_val = payload.fecha_boleta if (payload.fecha_boleta and payload.fecha_boleta.strip()) else None

        # Guardar en Supabase (CRM)
        supabase_data = {
            "id": payload.id,
            "usuario_nombre": payload.usuario_nombre,
            "usuario_email": payload.usuario_email,
            "departamento": payload.departamento,
            "centro_costo": payload.centro_costo,
            "rut_proveedor": payload.rut_proveedor,
            "fecha_boleta": fecha_boleta_val,
            "monto_total": payload.monto_total,
            "iva": payload.iva,
            "link_drive": payload.link_drive,
            "fecha_captura": fecha_captura,
            "tipo_transaccion": payload.tipo_transaccion,
            "origen_fondos": payload.origen_fondos,
            "monto_caja": payload.monto_caja,
            "monto_nc": payload.monto_nc,
            "clasificacion_sin_respaldo": payload.clasificacion_sin_respaldo,
            "estado": payload.estado,
            "factura_asociada": payload.factura_asociada,
            "comentarios_revisor": payload.comentarios_revisor,
            "descripcion": payload.descripcion
        }

        supabase.table("transacciones").insert(supabase_data).execute()
        
        # Enviar notificación por correo en segundo plano
        background_tasks.add_task(send_notification_email, supabase_data)

        return {"success": True, "data": supabase_data}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error guardando rendición: {str(e)}")
        return {"success": False, "error": "Error interno al guardar la rendición"}


@app.get("/history")
async def history(email: str):
    try:
        # Obtenemos historial directamente de Supabase (CRM)
        response = supabase.table("transacciones").select("*").eq("usuario_email", email).order("fecha_captura", desc=True).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"Error obteniendo historial: {str(e)}")
        return {"success": False, "error": "Error interno al obtener historial"}

@app.get("/capital/{email}")
async def get_capital(email: str):
    try:
        response = supabase.table("capital_entregado").select("monto_asignado").eq("email_usuario", email).execute()
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
async def update_expense_status(payload: UpdateStatusPayload, request: Request):
    # Validar que quien aprueba/rechaza sea Gerardo o José (Regla RBAC estricta)
    header_email = request.headers.get("X-User-Email", "").lower()
    if not header_email or header_email not in APPROVER_EMAILS:
        raise HTTPException(
            status_code=403, 
            detail="Solo Gerencia/Finanzas (Gerardo y José) tienen autorización para aprobar o rechazar rendiciones."
        )

    try:
        response = supabase.table("transacciones").update({
            "estado": payload.estado,
            "comentarios_revisor": payload.comentarios_revisor
        }).eq("id", payload.id).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"Error actualizando estado: {str(e)}")
        return {"success": False, "error": "Error interno al actualizar estado"}


@app.post("/export-sheets")
async def export_sheets(payload: ExportSheetsPayload):
    try:
        overwrite_sheets(payload.rows)
        return {"success": True, "message": "Datos sincronizados con Google Sheets"}
    except Exception as e:
        print(f"Error exportando a Sheets: {str(e)}")
        return {"success": False, "error": "Error interno al exportar a Sheets"}


@app.delete("/expense/{expense_id}")
async def delete_expense(expense_id: str, request: Request):
    # Validar permisos RBAC para eliminar registros
    header_email = request.headers.get("X-User-Email", "").lower()
    if not header_email or header_email not in APPROVER_EMAILS:
        raise HTTPException(
            status_code=403, 
            detail="Solo Gerencia/Finanzas (Gerardo y José) pueden eliminar registros."
        )

    try:
        # 1. Eliminar en Supabase
        supabase.table("transacciones").delete().eq("id", expense_id).execute()
        return {"success": True, "message": "Gasto eliminado correctamente"}
    except Exception as e:
        print(f"Error eliminando gasto: {str(e)}")
        return {"success": False, "error": "Error interno al eliminar el gasto"}


@app.put("/expense/{expense_id}")
async def edit_expense(expense_id: str, payload: EditExpenseRequest, request: Request):
    header_email = request.headers.get("X-User-Email", "").lower()
    is_approver = header_email in APPROVER_EMAILS

    try:
        # Obtener gasto original de Supabase
        response = supabase.table("transacciones").select("*").eq("id", expense_id).execute()
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Gasto no encontrado")

        old_expense = response.data[0]

        # Validación y recálculo de montos
        nuevo_monto = float(payload.monto_total)
        nuevo_iva = round((nuevo_monto * 19) / 119)

        final_origen = payload.origen_fondos or old_expense.get("origen_fondos", "Caja Principal")
        final_monto_caja = float(payload.monto_caja or 0)
        final_monto_nc = float(payload.monto_nc or 0)

        if final_origen == "Fondos Mixtos":
            if abs((final_monto_caja + final_monto_nc) - nuevo_monto) > 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"La suma de Monto Caja (${final_monto_caja:,.0f}) y Monto NC (${final_monto_nc:,.0f}) debe coincidir con el Monto Total (${nuevo_monto:,.0f})."
                )
        elif final_origen == "Casa Comercial":
            final_monto_caja = 0
            final_monto_nc = nuevo_monto
        elif payload.tipo_transaccion == "Sin Respaldo" or final_origen == "Cuentas por Recuperar":
            final_origen = "Cuentas por Recuperar"
            final_monto_caja = nuevo_monto
            final_monto_nc = 0
        else:
            final_origen = "Caja Principal"
            final_monto_caja = nuevo_monto
            final_monto_nc = 0

        # Protección RBAC: Solo los aprobadores autorizados pueden cambiar el estado existente
        if is_approver and payload.estado:
            final_estado = payload.estado
        else:
            final_estado = old_expense.get("estado", "Pendiente de Revisión")

        fecha_boleta_val = payload.fecha_boleta if (payload.fecha_boleta and payload.fecha_boleta.strip()) else None

        # Actualizar Supabase
        update_data = {
            "departamento": payload.departamento,
            "centro_costo": payload.centro_costo,
            "rut_proveedor": payload.rut_proveedor,
            "fecha_boleta": fecha_boleta_val,
            "monto_total": nuevo_monto,
            "iva": nuevo_iva,
            "tipo_transaccion": payload.tipo_transaccion,
            "origen_fondos": final_origen,
            "monto_caja": final_monto_caja,
            "monto_nc": final_monto_nc,
            "clasificacion_sin_respaldo": payload.clasificacion_sin_respaldo,
            "estado": final_estado,
            "factura_asociada": payload.factura_asociada,
            "comentarios_revisor": payload.comentarios_revisor,
            "descripcion": payload.descripcion
        }
        if payload.link_drive is not None:
            update_data["link_drive"] = payload.link_drive

        supabase.table("transacciones").update(update_data).eq("id", expense_id).execute()

        return {"success": True, "message": "Gasto actualizado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error editando gasto: {str(e)}")
        return {"success": False, "error": "Error interno al editar el gasto"}
