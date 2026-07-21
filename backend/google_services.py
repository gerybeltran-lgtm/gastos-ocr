import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# IDs leídos desde variables de entorno (nunca hardcodeados)
RENDER_SECRET_FILE = '/etc/secrets/credentials.json'
LOCAL_CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')

CREDENTIALS_FILE = RENDER_SECRET_FILE if os.path.exists(RENDER_SECRET_FILE) else LOCAL_CREDENTIALS_FILE

GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
SPREADSHEET_ID = os.environ.get("GOOGLE_SHEETS_ID", "")

if not FOLDER_ID or not SPREADSHEET_ID:
    import warnings
    warnings.warn("GOOGLE_DRIVE_FOLDER_ID o GOOGLE_SHEETS_ID no están configurados en las variables de entorno")

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

def get_google_services():
    if GOOGLE_CREDENTIALS_JSON:
        try:
            creds_info = json.loads(GOOGLE_CREDENTIALS_JSON)
            if "private_key" in creds_info:
                creds_info["private_key"] = creds_info["private_key"].replace('\\n', '\n')
            creds = service_account.Credentials.from_service_account_info(
                creds_info, scopes=SCOPES)
        except Exception as e:
            print(f"Error parseando GOOGLE_CREDENTIALS_JSON: {e}")
            raise
    else:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES)
            
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    return drive_service, sheets_service

def upload_image_to_drive(file_path, filename):
    drive_service, _ = get_google_services()
    
    file_metadata = {
        'name': filename,
        'parents': [FOLDER_ID]
    }
    media = MediaFileUpload(file_path, mimetype='image/jpeg', resumable=True)
    
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink',
        supportsAllDrives=True
    ).execute()
    
    return file.get('webViewLink')

def overwrite_sheets(rows):
    """
    Limpia la hoja (incluyendo encabezados) y escribe los nuevos datos exportados a demanda.
    """
    _, sheets_service = get_google_services()
    
    # 1. Limpiar datos anteriores (A1 hasta L)
    sheets_service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range='Hoja 1!A1:L'
    ).execute()
    
    if not rows:
        return {"success": True}
        
    # 2. Escribir las nuevas filas
    body = {
        'values': rows
    }
    
    result = sheets_service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range='Hoja 1!A1',
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    
    return result

if __name__ == "__main__":
    # Test connection
    print("Probando conexión a Google Workspace...")
    try:
        drive, sheets = get_google_services()
        print("Conexión exitosa a las APIs de Google.")
    except Exception as e:
        print(f"Error de conexión: {e}")
