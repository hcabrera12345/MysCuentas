import os
import json

def generate_config():
    print("--- Generador de Configuración para Render ---")
    print("Este script te ayudará a preparar los valores para las variables de entorno.\n")

    # 1. Google Credentials
    creds_file = 'credentials.json'
    if os.path.exists(creds_file):
        try:
            with open(creds_file, 'r') as f:
                content = json.load(f)
                # Dump to string with no newlines
                json_str = json.dumps(content)
                print(f"[OK] Archivo '{creds_file}' encontrado.")
                print("\n[COPIA ESTO PARA LA VARIABLE 'GOOGLE_CREDENTIALS_JSON']:")
                print("-" * 20)
                print(json_str) 
                print("-" * 20)
        except Exception as e:
            print(f"[ERROR] Error leyendo '{creds_file}': {e}")
    else:
        print(f"⚠️ No encontré '{creds_file}'. Asegúrate de poner el archivo en esta carpeta antes de correr el script.")
        print("   (Esto es necesario para que el bot pueda acceder a Google Sheets)")

    print("\n\n--- Otras Variables Necesarias ---")
    print("TELEGRAM_TOKEN:      (Copia el token que te dio @BotFather)")
    print("GEMINI_API_KEY:      (Copia tu API Key de Google AI Studio)")
    print("WEBHOOK_URL:         (La URL que Render te dará, ej: https://tu-app.onrender.com)")
    print("PYTHON_VERSION:      3.10.0")

if __name__ == "__main__":
    generate_config()
