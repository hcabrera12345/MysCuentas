import os
import google.generativeai as genai
from ai_handler import AIHandler
from dotenv import load_dotenv

load_dotenv()

def test_fixes():
    print("--- Testing Intent Fixes ---")
    
    # We need a valid API key for this test since it hits Gemini
    if not os.getenv("GEMINI_API_KEY"):
        print("No API Key, skipping live test.")
        return

    handler = AIHandler()
    
    # The specific failure cases reported by user
    cases = [
        "dame los gastos segun alimentos de hoy",
        "necesito el reporte de los gastos de hoy segun transporte",
        "50 bolivianos en taxi", # Control: Should be Expense
        "total gastado por Hernan"
    ]
    
    for text in cases:
        print(f"\n[INPUT]: '{text}'")
        try:
            intent = handler.parse_intent(text)
            print(f"[RESULT] Type: {intent.get('type')}")
            print(f"[DATA] Data: {intent.get('data')}")
            
            # Auto-verification
            if "reporte" in text or "dame" in text or "total" in text:
                if intent.get('type') != 'REPORT':
                    print("[FAIL] Should be REPORT")
            else:
                 if intent.get('type') != 'EXPENSE':
                    print("[FAIL] Should be EXPENSE")

        except Exception as e:
            print(f"[ERROR]: {e}")

if __name__ == "__main__":
    test_fixes()
