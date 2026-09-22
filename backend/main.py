import os
# Cargar variables de entorno desde .env antes de cualquier otra importación
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv no instalado, se usarán variables del sistema

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid
import tempfile
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
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

from accounting import VALID_STATUSES, as_db_number, calculate_vat, normalize_ledger
from security import (
    ADMIN_EMAILS,
    AuthenticatedUser,
    current_user,
    require_admin,
    require_approver,
)

def send_notification_email(data: dict):
    sender_email = os.environ.get("SENDER_EMAIL", "notificacionesevoltage@gmail.com")
    app_password = os.environ.get("EMAIL_PASSWORD", "")
    receiver_emails = sorted(ADMIN_EMAILS)

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
        if not app_password:
            return
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_emails, msg.as_string())
        print("Correo enviado exitosamente a los administradores.")
    except Exception as e:
        print(f"Error enviando correo: {str(e)}")

# Configurar credenciales de Google antes de importar el procesador
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
cred_path = os.path.join(BASE_DIR, 'credentials.json')

# Nunca persistir secretos provenientes del entorno en el disco de la aplicación.
if os.path.exists(cred_path):
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", cred_path)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Faltan SUPABASE_URL y/o SUPABASE_KEY")

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
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class StrictPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class SaveReceiptPayload(StrictPayload):
    id: str
    usuario_nombre: str
    usuario_email: str
    departamento: str
    centro_costo: str
    rut_proveedor: Optional[str] = None
    fecha_boleta: Optional[str] = None
    monto_total: float = Field(ge=0, le=1_000_000_000)
    iva: float | None = None
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

    @model_validator(mode="after")
    def validate_document_rules(self):
        if self.tipo_transaccion == "Factura" and not self.rut_proveedor:
            raise ValueError("rut_proveedor es obligatorio para Facturas")
        if self.tipo_transaccion == "Nota de Crédito" and not self.factura_asociada:
            raise ValueError("factura_asociada es obligatoria para Notas de Crédito")
        return self

class EditExpensePayload(StrictPayload):
    departamento: str
    centro_costo: str
    rut_proveedor: Optional[str] = None
    fecha_boleta: Optional[str] = None
    monto_total: float = Field(ge=0, le=1_000_000_000)
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

    @model_validator(mode="after")
    def validate_document_rules(self):
        if self.tipo_transaccion == "Factura" and not self.rut_proveedor:
            raise ValueError("rut_proveedor es obligatorio para Facturas")
        if self.tipo_transaccion == "Nota de Crédito" and not self.factura_asociada:
            raise ValueError("factura_asociada es obligatoria para Notas de Crédito")
        if self.estado not in VALID_STATUSES:
            raise ValueError("estado inválido")
        return self

class UpdateStatusPayload(StrictPayload):
    id: str
    estado: str
    comentarios_revisor: Optional[str] = None

    @field_validator("estado")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_STATUSES:
            raise ValueError("estado inválido")
        return value

class ExportPayload(StrictPayload):
    rows: list[list[str | int | float | None]] = Field(max_length=10_000)


def _has_valid_signature(path: Path, extension: str) -> bool:
    with path.open("rb") as source:
        header = source.read(12)
    if extension in {".jpg", ".jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".pdf":
        return header.startswith(b"%PDF-")
    return False

@app.post("/upload-receipt")
async def upload_receipt(
    file: UploadFile = File(...),
    userName: str = Form(...),
    userEmail: str = Form(...),
    department: str = Form(...),
    costCenter: str = Form(...),
    skip_ocr: Optional[str] = Form(None),
    user: AuthenticatedUser = Depends(current_user),
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
        temp_dir = tempfile.TemporaryDirectory(prefix="dealflow_")
        file_location = str(Path(temp_dir.name) / f"receipt{ext}")
        bytes_written = 0

        with open(file_location, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB por chunk
                bytes_written += len(chunk)
                if bytes_written > MAX_FILE_SIZE_BYTES:
                    buffer.close()
                    if os.path.exists(file_location):
                        os.remove(file_location)
                    raise HTTPException(
                        status_code=413,
                        detail=f"El archivo supera el tamaño máximo de {MAX_FILE_SIZE_MB}MB."
                    )
                buffer.write(chunk)

        if not _has_valid_signature(Path(file_location), ext):
            temp_dir.cleanup()
            raise HTTPException(status_code=400, detail="El contenido no coincide con el tipo de archivo declarado")

        try:
            # 1. Subir a Google Drive
            print(f"Subiendo a Google Drive: {file.filename}...")
            safe_original_name = Path(filename).name
            link_drive = upload_image_to_drive(file_location, f"{transaccion_id}_{safe_original_name}")
            
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
                    image_to_process = str(Path(temp_dir.name) / "page0.png")
                    with fitz.open(file_location) as pdf_doc:
                        if pdf_doc.page_count < 1 or pdf_doc.page_count > 100:
                            raise HTTPException(status_code=400, detail="PDF inválido")
                        page = pdf_doc.load_page(0)
                        pix = page.get_pixmap(dpi=150)
                        pix.save(image_to_process)

                try:
                    processed_img = preprocess_image(image_to_process, str(Path(temp_dir.name) / "optimized.jpg"))
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
            rut_prov = extracted_data.get("rut_proveedor") or extracted_data.get("rut") or ""
            rut_rec = extracted_data.get("rut_receptor") or ""
            es_ev = extracted_data.get("es_e_voltage", False)
            total_monto = extracted_data.get("monto_total") or extracted_data.get("total") or 0
            iva_val = extracted_data.get("iva") or (round((total_monto * 19) / 119) if total_monto else 0)

            response_data = {
                "id": transaccion_id,
                "usuario_nombre": user.name,
                "usuario_email": user.email,
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
                "message": "Boleta procesada exitosamente",
                "data": response_data
            }
            
        finally:
            temp_dir.cleanup()

    except HTTPException:
        raise
    except Exception as e:
        if "temp_dir" in locals():
            temp_dir.cleanup()
        import traceback
        err_msg = str(e)
        print(f"Error procesando boleta: {type(e).__name__}")
        traceback.print_exc()
        # Fallback estructurado en caso de error de OCR / API
        return {
            "success": False,
            "error": "No fue posible procesar el comprobante",
            "data": {
                "id": str(uuid.uuid4()) if 'uuid' in locals() else "temp-id",
                "usuario_nombre": user.name,
                "usuario_email": user.email,
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
async def save_receipt(
    data: SaveReceiptPayload,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(current_user),
):
    try:
        fecha_captura = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Validar y normalizar Ledger Segregado (Bolsas contables)
        final_origen, final_monto_caja, final_monto_nc, final_monto_total = normalize_ledger(
            data.monto_total, data.origen_fondos, data.tipo_transaccion, data.monto_caja, data.monto_nc
        )
        final_iva = calculate_vat(final_monto_total, data.tipo_transaccion)

        # Guardar en Supabase (CRM)
        supabase_data = {
            "id": data.id,
            "usuario_nombre": user.name,
            "usuario_email": user.email,
            "departamento": data.departamento,
            "centro_costo": data.centro_costo,
            "rut_proveedor": data.rut_proveedor,
            "fecha_boleta": data.fecha_boleta if data.fecha_boleta else None,
            "monto_total": as_db_number(final_monto_total),
            "iva": as_db_number(final_iva),
            "link_drive": data.link_drive,
            "fecha_captura": fecha_captura,
            "tipo_transaccion": data.tipo_transaccion,
            "origen_fondos": final_origen,
            "monto_caja": as_db_number(final_monto_caja),
            "monto_nc": as_db_number(final_monto_nc),
            "clasificacion_sin_respaldo": data.clasificacion_sin_respaldo,
            "estado": "Pendiente de Revisión",
            "factura_asociada": data.factura_asociada,
            "comentarios_revisor": None,
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
async def export_sheets(data: ExportPayload, _: AuthenticatedUser = Depends(require_admin)):
    try:
        safe_rows = [
            [("'" + cell) if isinstance(cell, str) and cell.startswith(("=", "+", "-", "@")) else cell for cell in row]
            for row in data.rows
        ]
        overwrite_sheets(safe_rows)
        return {"success": True}
    except Exception as e:
        print(f"Error exportando a Sheets: {str(e)}")
        return {"success": False, "error": "Error interno al exportar a Sheets"}

@app.get("/history")
async def get_history(user: AuthenticatedUser = Depends(current_user)):
    try:
        # Obtenemos solo los gastos del usuario que consulta
        response = supabase.table("transacciones").select("*").eq("usuario_email", user.email).order("fecha_captura", desc=True).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"Error obteniendo historial: {str(e)}")
        return {"success": False, "error": "Error interno al obtener historial"}

@app.get("/capital")
async def get_capital(user: AuthenticatedUser = Depends(current_user)):
    try:
        response = supabase.table("capital_entregado").select("monto_asignado").eq("email_usuario", user.email).execute()
        if response.data and len(response.data) > 0:
            return {"success": True, "monto_asignado": response.data[0]["monto_asignado"]}
        return {"success": True, "monto_asignado": 0}
    except Exception as e:
        print(f"Error obteniendo capital: {str(e)}")
        return {"success": False, "error": "Error interno al obtener capital"}


@app.get("/admin/history")
async def admin_history(_: AuthenticatedUser = Depends(require_admin)):
    try:
        # Obtenemos TODOS los gastos para el panel admin
        response = supabase.table("transacciones").select("*").order("fecha_captura", desc=True).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"Error obteniendo historial admin: {str(e)}")
        return {"success": False, "error": "Error interno al obtener historial admin"}

@app.post("/update-expense-status")
async def update_expense_status(data: UpdateStatusPayload, _: AuthenticatedUser = Depends(require_approver)):
    try:
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
async def delete_expense(expense_id: str, _: AuthenticatedUser = Depends(require_approver)):
    try:
        # 1. Eliminar en Supabase
        supabase.table("transacciones").delete().eq("id", expense_id).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error eliminando gasto: {str(e)}")
        return {"success": False, "error": "Error interno al eliminar el gasto"}

@app.put("/expense/{expense_id}")
async def edit_expense(
    expense_id: str,
    data: EditExpensePayload,
    user: AuthenticatedUser = Depends(current_user),
):
    try:
        # Obtener gasto original de Supabase
        response = supabase.table("transacciones").select("*").eq("id", expense_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Gasto no encontrado")
            
        old_expense = response.data[0]
        if not user.is_admin and old_expense.get("usuario_email", "").lower() != user.email:
            raise HTTPException(status_code=403, detail="No puede editar rendiciones de otro usuario")
        if not user.is_approver and old_expense.get("estado") not in {"Pendiente", "Pendiente de Revisión"}:
            raise HTTPException(status_code=409, detail="Solo puede editar rendiciones pendientes")
        
        # Calcular nuevo IVA (desde el Monto Total Bruto)
        final_origen, final_monto_caja, final_monto_nc, nuevo_monto = normalize_ledger(
            data.monto_total, data.origen_fondos, data.tipo_transaccion, data.monto_caja, data.monto_nc
        )
        nuevo_iva = calculate_vat(nuevo_monto, data.tipo_transaccion)

        # Protección RBAC: Solo los aprobadores autorizados pueden cambiar el estado existente
        if user.is_approver and data.estado:
            final_estado = data.estado
        else:
            final_estado = old_expense.get("estado", "Pendiente de Revisión")

        # Actualizar Supabase
        update_data = {
            "departamento": data.departamento,
            "centro_costo": data.centro_costo,
            "rut_proveedor": data.rut_proveedor,
            "fecha_boleta": data.fecha_boleta if data.fecha_boleta else None,
            "monto_total": as_db_number(nuevo_monto),
            "iva": as_db_number(nuevo_iva),
            "link_drive": data.link_drive if data.link_drive is not None else old_expense.get("link_drive"),
            "tipo_transaccion": data.tipo_transaccion,
            "origen_fondos": final_origen,
            "monto_caja": as_db_number(final_monto_caja),
            "monto_nc": as_db_number(final_monto_nc),
            "clasificacion_sin_respaldo": data.clasificacion_sin_respaldo,
            "estado": final_estado,
            "factura_asociada": data.factura_asociada,
            "comentarios_revisor": data.comentarios_revisor if user.is_approver else old_expense.get("comentarios_revisor"),
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
