import os
import sys

# Mock env vars for test
os.environ["TELEGRAM_TOKEN"] = "123:mock_token"
os.environ["GEMINI_API_KEY"] = "mock_key" 
# We don't need real keys, just enough to pass os.getenv checks if strictly enforced,
# though ExpenseBot might verify them.

from bot import ExpenseBot

def test_integrity():
    print("--- Testing Bot Integrity ---")
    try:
        # We assume handlers might fail auth but the class definition should load
        # We won't instantiate fully if it connects to Google Sheets real-time,
        # but importing 'bot' is the main test for NameError.
        print("[OK] bot.py imported successfully.")
        print("[OK] ExpenseBot class found.")
    except Exception as e:
        print(f"[FAIL] Syntax/Import Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_integrity()
