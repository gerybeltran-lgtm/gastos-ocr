import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
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

def send_notification_email(data: dict):
    sender_email = os.environ.get("SENDER_EMAIL", "notificacionesevoltage@gmail.com")
    app_password = os.environ.get("EMAIL_PASSWORD", "")
    receiver_emails = ["gerardo.beltran@e-voltage.cl", "jose.diaz@e-voltage.cl", "jorge.salas@e-voltage.cl"]

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
    with open(cred_path, "w") as f:
        f.write(os.environ.get("GOOGLE_CREDENTIALS_JSON"))

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path

# Supabase CRM Config
SUPABASE_URL = "https://msfvsjrubvzhkxzqjlhw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1zZnZzanJ1YnZ6aGt4enFqbGh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQxNjQ0MjQsImV4cCI6MjA3OTc0MDQyNH0.wP2YOTquFQvh_-VtY3Xv-tQWXq85HfqsIfK4E_XKZ9M"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

from procesador_gastos import preprocess_image, extract_text_from_image, parse_receipt_data
from google_services import upload_image_to_drive, overwrite_sheets
from typing import List, Optional

app = FastAPI(title="API Rendición de Gastos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EditExpenseRequest(BaseModel):
    departamento: str
    centro_costo: str
    rut_proveedor: str
    fecha_boleta: str
    monto_total: float
    tipo_transaccion: Optional[str] = "Boleta"
    origen_fondos: Optional[str] = "Caja Principal"
    estado: Optional[str] = "Pendiente de Revisión"
    factura_asociada: Optional[str] = ""
    comentarios_revisor: Optional[str] = ""
    descripcion: Optional[str] = ""

class SaveExpenseRequest(BaseModel):
    id: str
    usuario_nombre: str
    usuario_email: str
    departamento: str
    centro_costo: str
    rut_proveedor: str
    fecha_boleta: str
    monto_total: float
    iva: float
    link_drive: str
    tipo_transaccion: Optional[str] = "Boleta"
    origen_fondos: Optional[str] = "Caja Principal"
    estado: Optional[str] = "Pendiente de Revisión"
    factura_asociada: Optional[str] = ""
    comentarios_revisor: Optional[str] = ""
    descripcion: Optional[str] = ""

class ExportRequest(BaseModel):
    rows: List[list]

class UpdateStatusRequest(BaseModel):
    id: str
    estado: str
    comentarios_revisor: Optional[str] = ""

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
        # Generar ID único para este gasto
        expense_id = str(uuid.uuid4())
        
        # 1. Guardar archivo localmente de forma temporal
        temp_filename = f"temp_{uuid.uuid4()}_{file.filename}"
        temp_filepath = os.path.join(BASE_DIR, temp_filename)
        
        with open(temp_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1.5. Si es PDF, convertir la primera página a imagen
        if file.filename.lower().endswith(".pdf") or file.content_type == "application/pdf":
            try:
                doc = fitz.open(temp_filepath)
                if len(doc) > 0:
                    page = doc.load_page(0)
                    pix = page.get_pixmap(dpi=300)
                    pdf_img_filename = f"pdf_img_{uuid.uuid4()}.jpg"
                    pdf_img_filepath = os.path.join(BASE_DIR, pdf_img_filename)
                    pix.save(pdf_img_filepath)
                    
                    # Limpiar el PDF original y apuntar a la imagen generada
                    os.remove(temp_filepath)
                    temp_filepath = pdf_img_filepath
                    temp_filename = pdf_img_filename
                    
                    # Actualizar el nombre para cuando se suba a Google Drive
                    file.filename = pdf_img_filename
                doc.close()
            except Exception as e:
                print(f"Error procesando PDF: {str(e)}")
                return {"success": False, "error": f"Error leyendo PDF: {str(e)}"}
            
        # 2. Preprocesar imagen con OpenCV
        ocr_error = False
        datos_estructurados = {}
        upload_target = temp_filepath
        
        if skip_ocr.lower() != "true":
            try:
                optimized_filepath = os.path.join(BASE_DIR, f"opt_{temp_filename}")
                preprocess_image(temp_filepath, optimized_filepath)
                texto_extraido = extract_text_from_image(optimized_filepath)
                datos_estructurados = parse_receipt_data(texto_extraido)
                upload_target = optimized_filepath
            except Exception as e:
                print(f"OCR Error: {str(e)}")
                ocr_error = True
        
        # 5. Subir la imagen procesada (u original) a Google Drive
        drive_link = upload_image_to_drive(upload_target, file.filename)
        
        # 6. Preparar datos
        fecha_captura = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        monto_str = str(datos_estructurados.get("monto_total", "0")).replace(".", "").replace(",", "")
        try:
            monto_int = int(monto_str)
            iva = round(monto_int * 0.19)
        except:
            monto_int = 0
            iva = 0

        # NO Guardamos en BD todavía, solo devolvemos los datos para revisión
        supabase_data = {
            "id": expense_id,
            "usuario_nombre": userName,
            "usuario_email": userEmail,
            "departamento": department,
            "centro_costo": costCenter,
            "rut_proveedor": datos_estructurados.get("rut_proveedor", ""),
            "fecha_boleta": datos_estructurados.get("fecha", ""),
            "monto_total": monto_int,
            "iva": iva,
            "link_drive": drive_link
        }
        
        # 7. Limpiar archivos temporales
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        if 'optimized_filepath' in locals() and os.path.exists(optimized_filepath):
            os.remove(optimized_filepath)
            
        if ocr_error:
            return {
                "success": False,
                "error": "Error de lectura",
                "data": supabase_data
            }
        
        return {
            "success": True,
            "data": supabase_data
        }
        
    except Exception as e:
        print(f"Error procesando boleta: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/save-receipt")
async def save_receipt(data: SaveExpenseRequest, background_tasks: BackgroundTasks):
    try:
        fecha_captura = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Guardar en Supabase (CRM)
        supabase_data = {
            "id": data.id,
            "usuario_nombre": data.usuario_nombre,
            "usuario_email": data.usuario_email,
            "departamento": data.departamento,
            "centro_costo": data.centro_costo,
            "rut_proveedor": data.rut_proveedor,
            "fecha_boleta": data.fecha_boleta,
            "monto_total": data.monto_total,
            "iva": data.iva,
            "link_drive": data.link_drive,
            "fecha_captura": fecha_captura,
            "tipo_transaccion": data.tipo_transaccion,
            "origen_fondos": data.origen_fondos,
            "estado": data.estado,
            "factura_asociada": data.factura_asociada,
            "comentarios_revisor": data.comentarios_revisor,
            "descripcion": data.descripcion
        }
        supabase.table("transacciones").insert(supabase_data).execute()
        
        # Agregar el envío de correo como tarea en segundo plano
        background_tasks.add_task(send_notification_email, supabase_data)
        
        return {"success": True, "data": supabase_data}
    except Exception as e:
        print(f"Error guardando recibo: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/export-sheets")
async def export_sheets(data: ExportRequest):
    try:
        overwrite_sheets(data.rows)
        return {"success": True}
    except Exception as e:
        print(f"Error exportando a Sheets: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/history")
async def history(email: str):
    try:
        # Obtenemos historial directamente de Supabase (CRM)
        response = supabase.table("transacciones").select("*").eq("usuario_email", email).order("fecha_captura", desc=True).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"Error obteniendo historial: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/admin/history")
async def admin_history(email: str):
    ADMIN_EMAILS = ["gerardo.beltran@e-voltage.cl", "jose.diaz@e-voltage.cl", "jorge.salas@e-voltage.cl"]
    if email.lower() not in ADMIN_EMAILS:
        return {"success": False, "error": "Acceso denegado"}
    try:
        # Obtenemos TODOS los gastos para el panel admin
        response = supabase.table("transacciones").select("*").order("fecha_captura", desc=True).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"Error obteniendo historial admin: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/update-expense-status")
async def update_expense_status(data: UpdateStatusRequest):
    try:
        response = supabase.table("transacciones").update({
            "estado": data.estado,
            "comentarios_revisor": data.comentarios_revisor
        }).eq("id", data.id).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"Error updating status: {str(e)}")
        return {"success": False, "error": str(e)}

@app.delete("/expense/{expense_id}")
async def delete_expense(expense_id: str):
    try:
        # 1. Eliminar en Supabase
        supabase.table("transacciones").delete().eq("id", expense_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.put("/expense/{expense_id}")
async def edit_expense(expense_id: str, data: EditExpenseRequest):
    try:
        # Obtener gasto original de Supabase
        response = supabase.table("transacciones").select("*").eq("id", expense_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Gasto no encontrado")
            
        old_expense = response.data[0]
        
        # Calcular nuevo IVA
        nuevo_monto = data.monto_total
        nuevo_iva = round(nuevo_monto * 0.19)
        
        # Actualizar Supabase
        update_data = {
            "departamento": data.departamento,
            "centro_costo": data.centro_costo,
            "rut_proveedor": data.rut_proveedor,
            "fecha_boleta": data.fecha_boleta,
            "monto_total": nuevo_monto,
            "iva": nuevo_iva,
            "tipo_transaccion": data.tipo_transaccion,
            "origen_fondos": data.origen_fondos,
            "estado": data.estado,
            "factura_asociada": data.factura_asociada,
            "comentarios_revisor": data.comentarios_revisor,
            "descripcion": data.descripcion
        }
        supabase.table("transacciones").update(update_data).eq("id", expense_id).execute()
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
