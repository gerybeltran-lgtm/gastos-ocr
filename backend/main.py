import os
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import shutil
import uuid
from pydantic import BaseModel
from supabase import create_client, Client
import fitz  # PyMuPDF

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
from google_services import upload_image_to_drive, append_row_to_sheets, invalidate_row_in_sheets

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

@app.post("/upload-receipt")
async def upload_receipt(
    file: UploadFile = File(...),
    userName: str = Form(...),
    userEmail: str = Form(...),
    department: str = Form(...),
    costCenter: str = Form(...)
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
        optimized_filepath = os.path.join(BASE_DIR, f"opt_{temp_filename}")
        preprocess_image(temp_filepath, optimized_filepath)
        
        # 3. Extraer texto con Google Cloud Vision
        texto_extraido = extract_text_from_image(optimized_filepath)
        
        # 4. Extraer datos con Regex
        datos_estructurados = parse_receipt_data(texto_extraido)
        
        # 5. Subir la imagen procesada (u original) a Google Drive
        drive_link = upload_image_to_drive(optimized_filepath, file.filename)
        
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
            "rut_proveedor": datos_estructurados.get("rut_proveedor", "No detectado"),
            "fecha_boleta": datos_estructurados.get("fecha", "No detectada"),
            "monto_total": monto_int,
            "iva": iva,
            "link_drive": drive_link
        }
        
        # 7. Limpiar archivos temporales
        os.remove(temp_filepath)
        os.remove(optimized_filepath)
        
        return {
            "success": True,
            "data": supabase_data
        }
        
    except Exception as e:
        print(f"Error procesando boleta: {str(e)}")
        return {"success": False, "error": str(e)}

@app.post("/save-receipt")
async def save_receipt(data: SaveExpenseRequest):
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
            "fecha_captura": fecha_captura
        }
        supabase.table("gastos").insert(supabase_data).execute()

        # Guardar en Google Sheets
        fila_sheets = [
            data.id,
            "Válido",
            fecha_captura,
            data.usuario_nombre,
            data.usuario_email,
            data.departamento,
            data.centro_costo,
            data.rut_proveedor,
            data.fecha_boleta,
            data.monto_total,
            data.iva,
            data.link_drive
        ]
        append_row_to_sheets(fila_sheets)
        
        return {"success": True, "data": supabase_data}
    except Exception as e:
        print(f"Error guardando recibo: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/history")
async def history(email: str):
    try:
        # Obtenemos historial directamente de Supabase (CRM)
        response = supabase.table("gastos").select("*").eq("usuario_email", email).order("fecha_captura", desc=True).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"Error obteniendo historial: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/admin/history")
async def admin_history(email: str):
    ADMIN_EMAILS = ["gerardo.beltran@e-voltage.cl", "jose.diaz@e-voltage.cl"]
    if email not in ADMIN_EMAILS:
        return {"success": False, "error": "Acceso denegado"}
    try:
        # Obtenemos TODOS los gastos para el panel admin
        response = supabase.table("gastos").select("*").order("fecha_captura", desc=True).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print(f"Error obteniendo historial admin: {str(e)}")
        return {"success": False, "error": str(e)}

@app.delete("/expense/{expense_id}")
async def delete_expense(expense_id: str):
    try:
        # 1. Invalidar en Google Sheets
        invalidate_row_in_sheets(expense_id)
        # 2. Eliminar en Supabase
        supabase.table("gastos").delete().eq("id", expense_id).execute()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.put("/expense/{expense_id}")
async def edit_expense(expense_id: str, data: EditExpenseRequest):
    try:
        # Obtener gasto original de Supabase
        response = supabase.table("gastos").select("*").eq("id", expense_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Gasto no encontrado")
            
        old_expense = response.data[0]
        
        # 1. Invalidar la fila vieja en Google Sheets
        invalidate_row_in_sheets(expense_id)
        
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
            "iva": nuevo_iva
        }
        supabase.table("gastos").update(update_data).eq("id", expense_id).execute()
        
        # 2. Agregar nueva fila Válida al Sheets
        fecha_captura = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fila_sheets = [
            expense_id,
            "Válido (Editado)",
            fecha_captura,
            old_expense.get("usuario_nombre"),
            old_expense.get("usuario_email"),
            data.departamento,
            data.centro_costo,
            data.rut_proveedor,
            data.fecha_boleta,
            nuevo_monto,
            nuevo_iva,
            old_expense.get("link_drive")
        ]
        append_row_to_sheets(fila_sheets)
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
