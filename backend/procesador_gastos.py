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
        RENDER_SECRET_FILE = '/etc/secrets/credentials.json'
        LOCAL_CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        
        if os.path.exists(RENDER_SECRET_FILE):
            _vision_creds = service_account.Credentials.from_service_account_file(RENDER_SECRET_FILE, scopes=scopes)
        else:
            creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
            if creds_json:
                creds_info = json.loads(creds_json)
                if "private_key" in creds_info:
                    creds_info["private_key"] = creds_info["private_key"].replace('\\n', '\n')
                
                _vision_creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
            elif os.path.exists(LOCAL_CREDENTIALS_FILE):
                _vision_creds = service_account.Credentials.from_service_account_file(LOCAL_CREDENTIALS_FILE, scopes=scopes)
            else:
                _vision_creds = None
    return _vision_creds

def extract_text_from_image(image_path: str) -> str:
    creds = get_vision_creds()
    if not creds:
        # Fallback para local si no hay credenciales (usar application default credentials con google.auth.default)
        creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        
    # Obtener token OAuth usando httplib2 (porque requests falla en Render con Invalid JWT)
    import google_auth_httplib2
    import httplib2
    
    try:
        http_client = httplib2.Http()
        auth_request = google_auth_httplib2.Request(http_client)
        creds.refresh(auth_request)
        token = creds.token
    except Exception as e:
        email = getattr(creds, 'service_account_email', 'unknown')
        raise Exception(f"[{email}] Error refrescando token: {str(e)}")
        
    url = "https://vision.googleapis.com/v1/images:annotate"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    with open(image_path, "rb") as image_file:
        content = image_file.read()

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
            token_prefix = token[:10] if token else "None"
            raise Exception(f"[{email}] Error en Vision API REST (Token:{token_prefix}): {response.status_code} {response.text}")
        
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


EVOLTAGE_RUT_CLEAN = "771700632"
EVOLTAGE_RUT_FORMATTED = "77.170.063-2"

def clean_rut(rut_str: str) -> str:
    if not rut_str:
        return ""
    return re.sub(r'[^0-9kK]', '', rut_str).upper()

def format_rut(rut_str: str) -> str:
    clean = clean_rut(rut_str)
    if len(clean) < 2:
        return rut_str.strip().upper()
    body, dv = clean[:-1], clean[-1]
    parts = []
    while len(body) > 3:
        parts.insert(0, body[-3:])
        body = body[:-3]
    parts.insert(0, body)
    return '.'.join(parts) + '-' + dv

def parse_receipt_data(text: str) -> dict:
    """
    Analiza el texto extraído por OCR y estructura los datos contables:
    - RUT Proveedor (vendedor)
    - RUT Receptor (verifica si es E-Voltage SpA: 77.170.063-2)
    - Fecha
    - Monto Total, Neto e IVA
    """
    datos = {
        "rut_proveedor": None,
        "rut": None,
        "rut_receptor": None,
        "es_e_voltage": False,
        "fecha": None,
        "fecha_boleta": None,
        "monto_total": 0,
        "total": 0,
        "iva": 0,
        "neto": 0
    }

    if not text:
        return datos

    # 1. Extracción y Clasificación de RUTs
    rut_pattern = r'\b(\d{1,2}(?:\.?\d{3}){2}-[\dkK]|\d{7,8}-[\dkK])\b'
    found_ruts = re.findall(rut_pattern, text, re.IGNORECASE)

    vendor_ruts = []
    for r in found_ruts:
        formatted = format_rut(r)
        clean = clean_rut(r)
        if clean == EVOLTAGE_RUT_CLEAN:
            datos["rut_receptor"] = EVOLTAGE_RUT_FORMATTED
            datos["es_e_voltage"] = True
        else:
            if formatted not in vendor_ruts:
                vendor_ruts.append(formatted)

    if vendor_ruts:
        datos["rut_proveedor"] = vendor_ruts[0]
        datos["rut"] = vendor_ruts[0]
    elif found_ruts and not datos["es_e_voltage"]:
        formatted_single = format_rut(found_ruts[0])
        datos["rut_proveedor"] = formatted_single
        datos["rut"] = formatted_single

    # 2. Extracción de Fecha
    fecha_pattern1 = r'\b(0?[1-9]|[12][0-9]|3[01])[-/.](0?[1-9]|1[012])[-/.](20\d\d)\b'
    f_match1 = re.search(fecha_pattern1, text)
    if f_match1:
        d = f_match1.group(1).zfill(2)
        m = f_match1.group(2).zfill(2)
        y = f_match1.group(3)
        datos["fecha"] = f"{y}-{m}-{d}"
        datos["fecha_boleta"] = f"{y}-{m}-{d}"
    else:
        fecha_pattern2 = r'\b(20\d\d)[-/.](0?[1-9]|1[012])[-/.](0?[1-9]|[12][0-9]|3[01])\b'
        f_match2 = re.search(fecha_pattern2, text)
        if f_match2:
            y = f_match2.group(1)
            m = f_match2.group(2).zfill(2)
            d = f_match2.group(3).zfill(2)
            datos["fecha"] = f"{y}-{m}-{d}"
            datos["fecha_boleta"] = f"{y}-{m}-{d}"

    # 3. Extracción de Monto Total
    total_patterns = [
        r'(?i)(?:TOTAL\s*A\s*PAGAR|MONTO\s*TOTAL|TOTAL\s*PAGAR)[^\d\n]*[\$]?\s*(\d[\d\.]*)',
        r'(?i)(?<!SUB)(?<!SUB-)TOTAL[^\d\n]*[\$]?\s*(\d[\d\.]*)',
        r'(?i)\bTOTAL\b\s+[\$]?\s*(\d[\d\.]*)'
    ]
    
    total_val = None
    for pat in total_patterns:
        matches = re.findall(pat, text)
        if matches:
            for m in matches:
                clean_num = m.replace('.', '').strip()
                if clean_num.isdigit():
                    v = int(clean_num)
                    if v > 100:
                        total_val = v
                        break
        if total_val:
            break

    if not total_val:
        dollar_matches = re.findall(r'\$\s*([\d\.]+)', text)
        cands = []
        for m in dollar_matches:
            clean_num = m.replace('.', '').strip()
            if clean_num.isdigit():
                cands.append(int(clean_num))
        if cands:
            total_val = max(cands)

    if total_val:
        datos["monto_total"] = total_val
        datos["total"] = total_val
        datos["iva"] = round((total_val * 19) / 119)
        datos["neto"] = total_val - datos["iva"]

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
        print(f"RUT Receptor: {datos_estructurados['rut_receptor']}")
        print(f"Es E-Voltage: {datos_estructurados['es_e_voltage']}")
        print(f"Fecha: {datos_estructurados['fecha']}")
        print(f"Monto Total: ${datos_estructurados['monto_total']}")
        print(f"IVA: ${datos_estructurados['iva']}")
        
    except Exception as e:
        print(f"Ocurrió un error en el flujo: {str(e)}")
