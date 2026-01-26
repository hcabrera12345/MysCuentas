from sheets_handler import SheetsHandler
import pandas as pd

def check():
    try:
        print("Connecting to Google Sheets...")
        sheets = SheetsHandler()
        
        # Get all records
        data = sheets.sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty:
            print("The sheet is empty.")
            return

        print(f"\n[OK] Connection Successful!")
        print(f"Total entries found: {len(df)}")
        print("\nLast 5 entries recorded:")
        print(df.tail(5)[['Fecha', 'Categoría', 'Item', 'Monto', 'Usuario']].to_string(index=False))
        
    except Exception as e:
        print(f"Error connecting or reading sheet: {e}")

if __name__ == "__main__":
    check()
