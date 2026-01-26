import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

class SheetsAdapter:
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
                # Fallback: Look in parent directory if we are running from backend subdir
                parent_creds = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'credentials.json')
                if os.path.exists(parent_creds):
                    self.creds = ServiceAccountCredentials.from_json_keyfile_name(parent_creds, self.scope)
                else:
                    raise FileNotFoundError("Credentials not found (Env var GOOGLE_CREDENTIALS_JSON or file credentials.json)")

            self.client = gspread.authorize(self.creds)
            self.spreadsheet = self.client.open(spreadsheet_name)
            self.sheet = self.spreadsheet.sheet1
            
            # Ensure headers exist
            self._ensure_headers()

        except Exception as e:
            print(f"Error connecting to Sheets: {e}")
            raise

    def _ensure_headers(self):
        """Ensures the main sheet has the correct headers, including 'Usuario'."""
        try:
            headers = self.sheet.row_values(1)
            expected = ["Fecha", "Categoría", "Item", "Monto", "Moneda", "Usuario"]
            
            if not headers:
                self.sheet.append_row(expected)
            elif "Usuario" not in headers:
                col_index = len(headers) + 1
                self.sheet.update_cell(1, col_index, "Usuario")
        except Exception as e:
            print(f"Error checking headers: {e}")

    def get_categories(self):
        try:
            try:
                config_sheet = self.spreadsheet.worksheet("Config")
            except gspread.WorksheetNotFound:
                config_sheet = self.spreadsheet.add_worksheet(title="Config", rows=100, cols=2)
                config_sheet.append_row(["Categorías Válidas"])
                defaults = ["Alimentos", "Transporte", "Hogar", "Servicios", "Entretenimiento", "Salud", "Otros"]
                cell_list = config_sheet.range(f'A2:A{len(defaults)+1}')
                for i, cell in enumerate(cell_list):
                    cell.value = defaults[i]
                config_sheet.update_cells(cell_list)
                return defaults

            cats = config_sheet.col_values(1)[1:] 
            return [c for c in cats if c.strip()]
        except Exception as e:
            print(f"Error fetching categories: {e}")
            return ["Alimentos", "Transporte", "Hogar", "Servicios", "Entretenimiento", "Salud", "Otros"]

    def add_expense(self, date, category, item, amount, currency, user_name="Unknown"):
        try:
            row = [date, category, item, amount, currency, user_name]
            self.sheet.append_row(row)
            return True
        except Exception as e:
            print(f"Error adding expense: {e}")
            return False

    def get_all_records(self):
        return self.sheet.get_all_records()

    def delete_last_entry(self, user_name: str) -> str:
        try:
            records = self.sheet.get_all_values()
            for i in range(len(records) - 1, 0, -1):
                row = records[i]
                headers = records[0]
                try:
                    user_idx = headers.index("Usuario")
                except ValueError:
                    user_idx = 5 

                if len(row) > user_idx and row[user_idx] == user_name:
                    deleted_item = f"{row[2]} ({row[3]} {row[4]})"
                    self.sheet.delete_rows(i + 1)
                    return deleted_item
            return None
        except Exception as e:
            print(f"Error deleting entry: {e}")
            return None
