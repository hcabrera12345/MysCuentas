import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

class SheetsHandler:
    def __init__(self, json_keyfile_name='credentials.json', spreadsheet_name='Gastos'):
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Check if credentials are provided via env var (Render style) or file (Local style)
        json_creds = os.getenv("GOOGLE_CREDENTIALS_JSON")
        
        try:
            if json_creds:
                creds_dict = json.loads(json_creds)
                self.creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.scope)
            elif os.path.exists(json_keyfile_name):
                 self.creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile_name, self.scope)
            else:
                raise FileNotFoundError("Credentials not found (Env var GOOGLE_CREDENTIALS_JSON or file credentials.json)")

            self.client = gspread.authorize(self.creds)
            self.sheet = self.client.open(spreadsheet_name).sheet1
        except Exception as e:
            print(f"Error connecting to Sheets: {e}")
            raise

    def add_expense(self, date, category, item, amount, currency):
        try:
            row = [date, category, item, amount, currency]
            self.sheet.append_row(row)
            return True
        except Exception as e:
            print(f"Error adding expense: {e}")
            return False

    def get_all_records(self):
        return self.sheet.get_all_records()
