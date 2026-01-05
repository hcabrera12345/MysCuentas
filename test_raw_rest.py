import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

def test_rest():
    print("--- Testing Specific Models ---")
    candidates = ["gemini-2.0-flash-lite", "gemini-flash-latest", "gemini-2.5-flash-lite"]
    
    for model in candidates:
        print(f"\nModel: {model}")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [{"text": "Extract extraction: Gasto 50 bolivianos en taxi"}]
            }]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("✅ SUCCESS!")
                # print(response.json())
                return
            else:
                print(f"❌ FAILED: {response.text}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_rest()
