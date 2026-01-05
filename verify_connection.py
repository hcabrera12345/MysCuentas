import os
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

def test_connections():
    print("--- Verificando Conexiones ---")
    
    # 1. Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("X GEMINI_API_KEY no encontrada.")
    else:
        try:
            genai.configure(api_key=api_key)
            # Try to list models first to see what's available
            print("Modelos disponibles:")
            sub_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    sub_models.append(m.name)
            print(sub_models)

            model_name = 'gemini-1.5-flash'
            # Fallback check
            if f'models/{model_name}' not in sub_models and model_name not in sub_models:
                print(f"Warning: {model_name} no encontrado en la lista. Usando el primero disponible: {sub_models[0]}")
                model_name = sub_models[0].replace('models/', '')

            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Ping")
            print(f"V Gemini API: Conectado a {model_name}")
        except Exception as e:
            print(f"X Gemini API Error: {e}")

    # 2. Sheets
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        # Try to open the sheet mentioned in .env or default
        sheet_name = os.getenv("SPREADSHEET_NAME", "Gastos")
        try:
            sheet = client.open(sheet_name)
            print(f"V Google Sheets: Conectado a '{sheet_name}'")
        except gspread.SpreadsheetNotFound:
            print(f"X Google Sheets: No encontre la hoja '{sheet_name}'. Crea una hoja con ese nombre.")
    except Exception as e:
        print(f"X Google Sheets Error: {e}")

if __name__ == "__main__":
    test_connections()
