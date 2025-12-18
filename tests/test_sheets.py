import sys
import os

# Fix Path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from MysCuentas.src.sheets import init_db

if __name__ == "__main__":
    print("Testing Sheets Connection...")
    sheet = init_db()
    if sheet:
        print(f"✅ SUCCESS: Connected to '{sheet.title}'")
        print(f"   URL: https://docs.google.com/spreadsheets/d/{sheet.spreadsheet.id}")
    else:
        print("❌ FAILURE: Could not connect to Sheet.")
        exit(1)
