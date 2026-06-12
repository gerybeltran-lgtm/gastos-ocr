import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Constantes (reemplaza con los tuyos si cambian)
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')
FOLDER_ID = '1Bdg6Rzcj3tjuFbESEFAkLT4iV5kVRFij'
SPREADSHEET_ID = '13uq1ouzbLlc1efCPaaFpqIxVM_x4e8a93KyVdbEPwUo'

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

def get_google_services():
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

def append_row_to_sheets(datos):
    """
    Agrega una fila al Google Sheets.
    """
    _, sheets_service = get_google_services()
    
    body = {
        'values': [datos]
    }
    
    result = sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='Hoja 1!A:L',
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    
    return result

def invalidate_row_in_sheets(expense_id: str):
    """
    Busca la fila por ID y marca la columna Estado como 'Inválido'
    Asume que el ID está en la columna A (índice 0) y el Estado en B (índice 1).
    """
    _, sheets_service = get_google_services()
    
    # 1. Leer todas las filas
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range='Hoja 1!A:B' # Solo leemos ID y Estado para ser rápidos
    ).execute()
    
    values = result.get('values', [])
    if not values:
        return False
        
    # 2. Buscar la fila (1-indexed para Sheets)
    row_index = -1
    for i, row in enumerate(values):
        if len(row) > 0 and row[0] == str(expense_id):
            row_index = i + 1 # +1 porque en sheets las filas empiezan en 1
            break
            
    if row_index == -1:
        return False # No se encontró
        
    # 3. Actualizar la celda de Estado (Columna B)
    body = {
        'values': [['Inválido']]
    }
    sheets_service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f'Hoja 1!B{row_index}',
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    
    return True

def get_user_expenses(user_email: str):
    """
    Obtiene todas las filas del Sheets y filtra por el email del usuario.
    Asume que el email está en la columna C (índice 2).
    """
    _, sheets_service = get_google_services()
    
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range='Hoja 1!A:J'
    ).execute()
    
    values = result.get('values', [])
    if not values:
        return []
        
    # Filtrar descartando la cabecera
    # Orden esperado: [Fechas Captura, Usuario, Email, Departamento, Centro de Costo, RUT, Fecha Boleta, Monto, IVA, Link]
    headers = values[0]
    expenses = []
    
    for row in values[1:]:
        # Asegurarse de que la fila tenga suficientes columnas para revisar el email (índice 2)
        if len(row) > 2 and row[2].strip().lower() == user_email.strip().lower():
            # Construir objeto seguro (llenar con string vacío si faltan columnas al final)
            expense = {
                "fecha_captura": row[0] if len(row) > 0 else "",
                "usuario": row[1] if len(row) > 1 else "",
                "email": row[2] if len(row) > 2 else "",
                "departamento": row[3] if len(row) > 3 else "",
                "centro_costo": row[4] if len(row) > 4 else "",
                "rut_proveedor": row[5] if len(row) > 5 else "",
                "fecha_boleta": row[6] if len(row) > 6 else "",
                "monto_total": row[7] if len(row) > 7 else "0",
                "iva": row[8] if len(row) > 8 else "0",
                "link_drive": row[9] if len(row) > 9 else ""
            }
            expenses.append(expense)
            
    # Ordenar por fecha de captura (más reciente primero)
    expenses.sort(key=lambda x: x["fecha_captura"], reverse=True)
    return expenses

if __name__ == "__main__":
    # Test connection
    print("Probando conexión a Google Workspace...")
    try:
        drive, sheets = get_google_services()
        print("Conexión exitosa a las APIs de Google.")
    except Exception as e:
        print(f"Error de conexión: {e}")
