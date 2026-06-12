import os
from google_services import get_google_services, FOLDER_ID, SPREADSHEET_ID

def check_permissions():
    drive, sheets = get_google_services()
    print(f"Checking access to Folder ID: {FOLDER_ID} with supportsAllDrives=True")
    try:
        folder = drive.files().get(
            fileId=FOLDER_ID, 
            fields="id, name",
            supportsAllDrives=True
        ).execute()
        print(f"SUCCESS: Can access folder '{folder.get('name')}'")
    except Exception as e:
        print(f"ERROR: Cannot access folder. {e}")

if __name__ == "__main__":
    check_permissions()
