import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

def list_models():
    print("--- Listing Models VIA REST ---")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"Found {len(models)} models.")
            for m in models:
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    print(f"AVAILABLE: {m['name']}")
        else:
            print(f"FAILED: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_models()
