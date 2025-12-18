import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
from dotenv import load_dotenv

# Load Env (Robust Path)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logger = logging.getLogger(__name__)

SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "MysCuentas_DB")
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')

def get_client():
    """Authenticates with Google."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if not os.path.exists(CREDENTIALS_FILE):
             # Cloud Mode: we might use ENV var for base64 credentials later, but for now log error
             logger.error(f"Credentials file not found at {CREDENTIALS_FILE}")
             return None
             
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logger.error(f"Auth Sheets Error: {e}")
        return None

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def init_db():
    """Initializes the Sheet with Retries."""
    client = get_client()
    if not client: return None
    
    try:
        sheet = client.open(SPREADSHEET_NAME).sheet1
        return sheet
    except gspread.SpreadsheetNotFound:
        try:
            logger.info("Sheet not found. Creating...")
            sh = client.create(SPREADSHEET_NAME)
            sh.share(client.auth.service_account_email, perm_type='user', role='owner')
            sheet = sh.sheet1
            # Flat Schema
            sheet.append_row(["Fecha", "Hora", "Usuario", "Monto", "Moneda", "Categoría", "Subcategoría", "Descripción", "Fuente"])
            return sheet
        except Exception as e:
            logger.error(f"Create Sheet Error: {e}")
            return None
