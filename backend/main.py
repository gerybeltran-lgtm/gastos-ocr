import os
# Cargar variables de entorno desde .env antes de cualquier otra importación
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import base64
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
                <p><strong>Email:</strong> {data.get('usuario_email')}</p>
                <p><strong>Departamento:</strong> {data.get('departamento')}</p>
                <p><strong>Centro de Costo:</strong> {data.get('centro_costo')}</p>
                <p><strong>Tipo de Transacción:</strong> {data.get('tipo_transaccion')}</p>
                <p><strong>Origen de Fondos:</strong> {data.get('origen_fondos', 'Caja Principal')}</p>
                <p><strong>RUT Proveedor:</strong> {data.get('rut_proveedor', 'N/A')}</p>
                <p><strong>N° Doc / Factura Asociada:</strong> {data.get('factura_asociada', 'N/A')}</p>
                <p><strong>Fecha Documento:</strong> {data.get('fecha_boleta', 'N/A')}</p>
                <p><strong>Monto Total:</strong> ${data.get('monto_total', 0):,.0f}</p>
                {f"<p><strong>Monto Caja Principal:</strong> ${data.get('monto_caja', 0):,.0f}</p>" if data.get('origen_fondos') == 'Fondos Mixtos' else ""}
                {f"<p><strong>Monto Casa Comercial (NC):</strong> ${data.get('monto_nc', 0):,.0f}</p>" if data.get('origen_fondos') == 'Fondos Mixtos' else ""}
                {f"<p><strong>Clasificación Sin Respaldo:</strong> {data.get('clasificacion_sin_respaldo')}</p>" if data.get('clasificacion_sin_respaldo') else ""}
                <p><strong>IVA:</strong> ${data.get('iva', 0):,.0f}</p>
                <p><strong>Estado:</strong> {data.get('estado', 'Pendiente de Revisión')}</p>
                {f"<p><strong>Descripción / Motivo:</strong> {data.get('descripcion')}</p>" if data.get('descripcion') else ""}
                {f"<p><strong>Respaldo Drive:</strong> <a href='{data.get('link_drive')}'>Ver archivo</a></p>" if data.get('link_drive') else ""}
            </div>
            <div style="background-color: #f1f5f9; padding: 15px; text-align: center; font-size: 12px; color: #64748b;">
                DealFlow Gastos &bull; Sistema de Rendiciones
            </div>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"DealFlow Gastos <{sender_email}>"
    msg["To"] = ", ".join(receiver_emails)
    msg.attach(MIMEText(html_content, "html"))

    try:
        if not app_password:
            print("AVISO: EMAIL_PASSWORD no configurada en variables de entorno. Correo omitido.")
            return
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_emails, msg.as_string())
        print("Correo enviado exitosamente a los administradores")
    except Exception as e:
        print(f"Error al enviar correo de notificación: {e}")

try:
    from google_services import upload_to_drive, append_to_sheets, overwrite_sheets
except ImportError:
    def upload_to_drive(file_content, filename):
        print("Aviso: google_services no encontrado. Simulando upload.")
        return "https://drive.google.com/dummy-link"
    def append_to_sheets(data):
        print("Aviso: google_services no encontrado. Simulando append.")
        return True
    def overwrite_sheets(rows):
        print("Aviso: google_services no encontrado. Simulando overwrite.")
        return True

try:
    from supabase_client import supabase
except ImportError:
    class DummySupabase:
        def table(self, name):
            return self
        def select(self, *args):
            return self
        def insert(self, data):
            return self
        def update(self, data):
            return self
        def delete(self):
            return self
        def eq(self, *args):
            return self
        def order(self, *args, **kwargs):
            return self
        def execute(self):
            return type('obj', (object,), {'data': []})
    supabase = DummySupabase()

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

app = FastAPI(title="API Rendición de Gastos")

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://gastos-ocr.vercel.app",
    "https://gastos-ocr-frontend.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class SaveExpenseRequest(BaseModel):
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

class EditExpenseRequest(BaseModel):
    departamento: str
    centro_costo: str
    rut_proveedor: Optional[str] = None
    fecha_boleta: Optional[str] = None
    monto_total: float
    tipo_transaccion: Optional[str] = "Boleta"
    origen_fondos: Optional[str] = "Caja Principal"
    monto_caja: Optional[float] = 0.0
    monto_nc: Optional[float] = 0.0
    clasificacion_sin_respaldo: Optional[str] = None
    estado: Optional[str] = "Pendiente de Revisión"
    factura_asociada: Optional[str] = None
    comentarios_revisor: Optional[str] = None
    descripcion: Optional[str] = None

class UpdateStatusRequest(BaseModel):
    id: str
    estado: str
    comentarios_revisor: Optional[str] = None

class ExportRequest(BaseModel):
    rows: List[List[str]]

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
        # 1. Validar extensión
        _, ext = os.path.splitext(file.filename or "")
        ext = ext.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Extensión de archivo no permitida ({ext}). Solo se aceptan: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # 2. Validar Content-Type
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido ({file.content_type}). Solo se aceptan imágenes (JPEG, PNG) y PDF."
            )

        # 3. Leer contenido y validar tamaño
        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise HTTPException(status_code=400, detail="El archivo está vacío.")

        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"El archivo excede el tamaño máximo permitido de {MAX_FILE_SIZE_MB}MB (tamaño actual: {file_size / (1024*1024):.1f}MB)."
            )

        # Determinar MIME type
        mime_type = file.content_type or ("application/pdf" if ext == ".pdf" else "image/jpeg")

        # 4. Subir a Google Drive
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = f"{timestamp}_{file.filename}"
        link_drive = upload_to_drive(content, safe_name)

        if skip_ocr == "true":
            parsed_data = {
                "rut_proveedor": "",
                "fecha_boleta": datetime.now().strftime("%Y-%m-%d"),
                "monto_total": 0,
                "iva": 0
            }
        else:
            if not GEMINI_API_KEY:
                raise HTTPException(status_code=500, detail="GEMINI_API_KEY no configurada")

            client = genai.Client(api_key=GEMINI_API_KEY)

            prompt = """
            Eres un experto en lectura de boletas y facturas chilenas.
            Analiza el documento adjunto y extrae los siguientes campos en formato JSON estricto:
            - rut_proveedor: El RUT de la empresa o emisor (ej: "76.123.456-7" o "12345678-9"). Si no es legible o no existe, retorna null.
            - fecha_boleta: Fecha de emisión en formato YYYY-MM-DD. Si no es legible, retorna la fecha de hoy.
            - monto_total: Monto total final a pagar (número entero o decimal, sin puntos de miles ni signo $). Si no es legible, retorna 0.
            - iva: Monto del IVA si está explícito o es factura. Si no aparece (típico en boletas), calcula IVA = round((monto_total * 19) / 119).

            Devuelve ÚNICAMENTE el bloque JSON, sin markdown, sin ```json```, solo texto JSON puro.
            Ejemplo:
            {"rut_proveedor": "76.452.123-K", "fecha_boleta": "2023-10-25", "monto_total": 15990, "iva": 2553}
            """

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Part.from_bytes(
                        data=content,
                        mime_type=mime_type,
                    ),
                    prompt
                ]
            )

            raw_text = response.text.strip()
            # Limpiar posibles bloques markdown
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            try:
                parsed_data = json.loads(raw_text)
            except json.JSONDecodeError:
                # Si Gemini falla en devolver JSON válido, fallback
                parsed_data = {
                    "rut_proveedor": None,
                    "fecha_boleta": datetime.now().strftime("%Y-%m-%d"),
                    "monto_total": 0,
                    "iva": 0
                }

        # Generar un ID único para la transacción
        import uuid
        transaccion_id = str(uuid.uuid4())

        return {
            "success": True,
            "data": {
                "id": transaccion_id,
                "usuario_nombre": userName,
                "usuario_email": userEmail,
                "departamento": department,
                "centro_costo": costCenter,
                "rut_proveedor": parsed_data.get("rut_proveedor"),
                "fecha_boleta": parsed_data.get("fecha_boleta"),
                "monto_total": parsed_data.get("monto_total", 0),
                "iva": parsed_data.get("iva", 0),
                "link_drive": link_drive
            }
        }

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
async def save_receipt(data: SaveExpenseRequest, background_tasks: BackgroundTasks):
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
async def export_sheets(data: ExportRequest):
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
            return {"success": True, "monto_asignado": response.data[0].get("monto_asignado", 0)}
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
async def update_expense_status(data: UpdateStatusRequest, request: Request):
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
async def edit_expense(expense_id: str, data: EditExpenseRequest, request: Request):
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
