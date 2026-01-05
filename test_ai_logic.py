import os
import google.generativeai as genai
from ai_handler import AIHandler
from dotenv import load_dotenv

# Load env vars
load_dotenv()

def test_extraction():
    print("--- Starting Local AI Test ---")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY is missing in .env")
        return

    print(f"[OK] API Key found: {api_key[:5]}...")

    test_cases = ["Gasto 50 bolivianos en taxi"] # Fast single test
    
    candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro",
        "gemini-pro",
        "gemini-1.0-pro"
    ]
    
    for model_name in candidates:
        print(f"\n--- Trying Model: {model_name} ---")
        try:
            handler = AIHandler() # Re-init clean
            handler.model = genai.GenerativeModel(model_name) # Force swap
            result = handler.process_text(test_cases[0])
            if result and "error" not in result:
                print(f"[SUCCESS] with {model_name}!")
                print(f"Result: {result}")
                return # Found a working one
            else:
                print(f"[FAILED] {model_name}: {result.get('error')}")
        except Exception as e:
            print(f"[ERROR] {model_name}: {e}")

if __name__ == "__main__":
    test_extraction()
