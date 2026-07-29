import cv2
import re
import os
import json
from google.cloud import vision
from google.oauth2 import service_account
import google.auth
import google.auth.transport.requests
import requests
import base64

def preprocess_image(input_path: str, output_path: str = "optimized_receipt.jpg") -> str:
    """
    Preprocesa la imagen de la boleta para mejorar la precisión del OCR.
    Aplica escala de grises y mejora el contraste.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"La imagen {input_path} no existe.")

    # 1. Leer imagen
    img = cv2.imread(input_path)
    
    if img is None:
        print(f"Advertencia: OpenCV no pudo leer la imagen {input_path}. Usando original.")
        return input_path

    # 2. Convertir a escala de grises
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 3. Mejorar contraste (Ecualización de Histograma Adaptativo - CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_img = clahe.apply(gray)

    # 4. Guardar y retornar la ruta de la imagen procesada
    cv2.imwrite(output_path, enhanced_img)
    return output_path


# Variables globales
_vision_creds = None

def get_vision_creds():
    global _vision_creds
    if _vision_creds is None:
        creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            creds_info = json.loads(creds_json)
            if "private_key" in creds_info:
                creds_info["private_key"] = creds_info["private_key"].replace('\\n', '\n')
            
            scopes = ['https://www.googleapis.com/auth/cloud-platform']
            _vision_creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
        else:
            _vision_creds = None
    return _vision_creds

def extract_text_from_image(image_path: str) -> str:
    creds = get_vision_creds()
    if not creds:
        # Fallback para local si no hay credenciales (usar application default credentials con google.auth.default)
        creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        
    # Obtener token OAuth
    auth_request = google.auth.transport.requests.Request()
    creds.refresh(auth_request)
    token = creds.token

    with open(image_path, "rb") as image_file:
        content = image_file.read()

    url = "https://vision.googleapis.com/v1/images:annotate"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "requests": [
            {
                "image": {
                    "content": base64.b64encode(content).decode("utf-8")
                },
                "features": [
                    {
                        "type": "DOCUMENT_TEXT_DETECTION"
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            email = getattr(creds, 'service_account_email', 'unknown')
            raise Exception(f"[{email}] Error en Vision API REST: {response.status_code} {response.text}")
        
        resp_json = response.json()
        responses = resp_json.get("responses", [])
        if not responses or "fullTextAnnotation" not in responses[0]:
            return ""
        return responses[0]["fullTextAnnotation"]["text"]
    except Exception as e:
        email = getattr(creds, 'service_account_email', 'unknown')
        if not isinstance(e, Exception) or not str(e).startswith(f"[{email}]"):
            raise Exception(f"[{email}] {str(e)}")
        raise e


def parse_receipt_data(text: str) -> dict:
    """
    Utiliza expresiones regulares (Regex) para extraer RUT, Fecha y Monto Total.
    """
    datos = {
        "rut_proveedor": None,
        "fecha": None,
        "monto_total": None
    }

    # 1. Extraer RUT chileno
    rut_pattern = r'\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b'
    rut_match = re.search(rut_pattern, text)
    if rut_match:
        datos["rut_proveedor"] = rut_match.group(0).upper()

    # 2. Extraer Fecha
    fecha_pattern = r'\b(0[1-9]|[12][0-9]|3[01])[-/](0[1-9]|1[012])[-/](20\d\d)\b'
    fecha_match = re.search(fecha_pattern, text)
    if fecha_match:
        datos["fecha"] = fecha_match.group(0)

    # 3. Extraer Monto Total
    # Estrategia 1: Buscar TOTAL explícito (ignorando SUB-TOTAL) en la misma línea
    monto_pattern = r'(?i)(?<!SUB)(?<!SUB-)TOTAL[^\n\d]*\$?\s*([\d\.]+)'
    montos_encontrados = re.findall(monto_pattern, text)
    
    # Estrategia 2: Si no encuentra TOTAL válido, tomar el último monto con signo $ del documento
    if not montos_encontrados:
        montos_encontrados = re.findall(r'\$\s*([\d\.]+)', text)
        
    if montos_encontrados:
        posible_total = montos_encontrados[-1].replace('.', '').strip()
        if posible_total.isdigit():
            datos["monto_total"] = int(posible_total)

    return datos


if __name__ == "__main__":
    imagen_original = "foto_boleta.jpg"
    
    try:
        print("1. Preprocesando imagen con OpenCV...")
        imagen_optimizada = preprocess_image(imagen_original)
        
        print("2. Extrayendo texto con Google Cloud Vision API...")
        texto_extraido = extract_text_from_image(imagen_optimizada)
        
        print("3. Analizando datos mediante Regex...")
        datos_estructurados = parse_receipt_data(texto_extraido)
        
        print("\n--- RESULTADO FINAL ---")
        print(f"RUT Proveedor: {datos_estructurados['rut_proveedor']}")
        print(f"Fecha: {datos_estructurados['fecha']}")
        print(f"Monto Total: ${datos_estructurados['monto_total']}")
        
    except Exception as e:
        print(f"Ocurrió un error en el flujo: {str(e)}")
