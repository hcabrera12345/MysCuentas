import pandas as pd
import matplotlib
matplotlib.use('Agg') # Server mode
import matplotlib.pyplot as plt
import io
import datetime

class ReportEngine:
    def __init__(self, data):
        """
        data: List of dicts from SheetsHandler.get_all_records()
        Expected Keys (Spanish Headers): Fecha, Categoría, Item, Monto, Moneda, Usuario
        """
        self.raw_df = pd.DataFrame(data)
        
        # Standardize Columns
        # Rename map: Spanish -> Internal English (Robust mapping)
        # We need to find the actual columns in raw_df because of potential accents/case quirks
        
        col_map = {}
        for col in self.raw_df.columns:
            c = col.lower().strip()
            if 'fecha' in c: col_map[col] = 'date'
            elif 'categor' in c: col_map[col] = 'category' # Matches Categoria/Categoría
            elif 'item' in c or 'descrip' in c: col_map[col] = 'item'
            elif 'monto' in c: col_map[col] = 'amount'
            elif 'moneda' in c: col_map[col] = 'currency'
            elif 'usuario' in c: col_map[col] = 'user'
            
        self.df = self.raw_df.rename(columns=col_map)
        
        # Normalize Data Types
        if not self.df.empty:
            try:
                # Force numeric, coercion errors become NaN (handle gracefully?)
                # Cleaning weird characters from amounts if any
                self.df['amount'] = pd.to_numeric(self.df['amount'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                
                # Robust Date Parsing (Sheet might use DD/MM/YYYY or YYYY-MM-DD)
                # Try explicit format first, then inference
                self.df['date'] = pd.to_datetime(self.df['date'], dayfirst=True, errors='coerce')
                
                # Check for any failures to force another strategy if needed
                if self.df['date'].isnull().all() and not self.df.empty:
                     print("DEBUG: All dates came back NaT, trying dayfirst=False or mixed")
                     self.df['date'] = pd.to_datetime(self.raw_df.iloc[:, 0], errors='coerce') # Fallback to raw col 0
                
                # Normalize Timezone (Remove timezone info to compare with naive 'now')
                if pd.api.types.is_datetime64_any_dtype(self.df['date']):
                     self.df['date'] = self.df['date'].dt.tz_localize(None)

                # Lowercase string columns for easier filtering
                if 'user' in self.df.columns:
                    self.df['user_norm'] = self.df['user'].astype(str).str.lower()
                if 'category' in self.df.columns:
                    self.df['category_norm'] = self.df['category'].astype(str).str.lower()
            except Exception as e:
                print(f"Data conversion error: {e}")
                
        print(f"DEBUG: DataFrame Head:\n{self.df.head()}")
        print(f"DEBUG: Dtypes:\n{self.df.dtypes}")

    def filter_data(self, time_range='all', filter_user=None, filter_category=None):
        if self.df.empty:
            return self.df
            
        df_filtered = self.df.copy()
        today = datetime.datetime.now()
        
        # 1. Date Filter
        if 'date' in df_filtered.columns and pd.api.types.is_datetime64_any_dtype(df_filtered['date']):
            # Clean time range string
            tr = str(time_range).lower().strip()
            print(f"DEBUG: Filtering for time_range: {tr}")
            
            if 'today' in tr or 'hoy' in tr:
                df_filtered = df_filtered[df_filtered['date'].dt.date == today.date()]
            elif 'week' in tr or 'semana' in tr:
                start_date = today - datetime.timedelta(days=7)
                df_filtered = df_filtered[df_filtered['date'] >= start_date]
            elif 'month' in tr or 'mes' in tr:
                # Compare year and month
                # Ensure we are comparing integers for month/year
                df_filtered = df_filtered[
                    (df_filtered['date'].dt.month == today.month) & 
                    (df_filtered['date'].dt.year == today.year)
                ]
            elif 'days' in tr or 'dias' in tr:
                # Extract number from "3 days"
                try:
                    import re
                    match = re.search(r'\d+', tr)
                    days = int(match.group()) if match else 7
                    # Ensure start_date is naive
                    start_date = (today - datetime.timedelta(days=days)).replace(tzinfo=None)
                    df_filtered = df_filtered[df_filtered['date'] >= start_date]
                except Exception as e:
                    print(f"DEBUG: Error parsing days filter: {e}")
                    pass # Fallback to all if parsing fails
        else:
            print("DEBUG: 'date' column missing or not datetime dtype")
            # Fallback: If no date column, maybe just return everything? Or logic by string?
            # For now warning only.
        
        # 2. User Filter (Fuzzy match)
        if filter_user and 'user' in df_filtered.columns:
            # Simple contains check
            df_filtered = df_filtered[df_filtered['user_norm'].str.contains(filter_user.lower(), na=False)]

        # 3. Category Filter
        if filter_category and 'category' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['category_norm'].str.contains(filter_category.lower(), na=False)]

        return df_filtered

    def generate_report(self, intent_data):
        """Unified entry point for report generation options."""
        query_type = intent_data.get('query_type', 'total')
        time_range = intent_data.get('time_range', 'all')
        filter_user = intent_data.get('filter_user')
        filter_category = intent_data.get('category') 

        df_subset = self.filter_data(time_range, filter_user, filter_category)
        
        if df_subset.empty:
            return {'type': 'text', 'content': f"ℹ️ No encontré registros para: {time_range}."}

        # 1. GRAPH REQUEST
        if query_type == 'graph':
            buf = self._make_graph(df_subset, time_range)
            if buf:
                path = "temp_chart.png"
                with open(path, "wb") as f:
                    f.write(buf.getbuffer())
                return {'type': 'image', 'path': path}
            else:
                 return {'type': 'text', 'content': "No hay suficientes datos para graficar."}
        
        # Data Aggregation for Text/Table
        # Group by User + Category
        if 'user' in df_subset.columns and 'category' in df_subset.columns:
            grouped = df_subset.groupby(['user', 'category'])['amount'].sum().reset_index()
        else:
            # Fallback if columns missing
            grouped = df_subset.groupby('category')['amount'].sum().reset_index()
            grouped['user'] = 'Desconocido'

        # 2. TABLE REQUEST (explicit format requested)
        # Format: USUARIO / CATEGORIA / TOTAL
        if query_type == 'list': # "Table" button maps to 'list' or we can add specific handling if 'format' passed
             # The bot passes 'list' by default for text/table buttons, distinction is in UI display? 
             # Wait, user said "si le pido reporte... respuesta por tabla". 
             # Ideally the bot should detect "tabla" keyword or button press.
             # The Button handler sends callback `rep_table` which we must handle.
             # But here we just return the content. 
             # Text vs Table is often just formatting.
             
             # Let's generate both formats and let the caller decide or return based on a flag?
             # The caller `button_handler` decides if it wraps in ``` code block ```.
             # But the CONTENT inside needs to be aligned for table.
             
             # We will return a formatted string that looks like a table for Monospace.
             table_lines = [f"{'USUARIO':<10} | {'CATEGORIA':<15} | {'TOTAL':<8}"]
             table_lines.append("-" * 40)
             for _, row in grouped.iterrows():
                 u = str(row['user'])[:10]
                 c = str(row['category'])[:15]
                 a = f"{row['amount']:.2f}"
                 table_lines.append(f"{u:<10} | {c:<15} | {a:<8}")
             
             table_content = "\n".join(table_lines)
             
             # 3. TEXT REQUEST (Narrative)
             # "El usuario xxxx gastó en categoria 1, x bs..."
             text_lines = []
             for _, row in grouped.iterrows():
                 text_lines.append(f"👤 El usuario *{row['user']}* gastó en *{row['category']}*: {row['amount']:.2f} Bs.")
             
             text_content = "\n".join(text_lines)
             
             # Return both components so Bot can choose based on user interaction?
             # ReportEngine doesn't know about buttons.
             # Hack: We return a special dict or just the Text version by default?
             # The user prompt implies: "If I ask for table... If I ask for text..."
             
             # If intent_data has 'format' (from AI or button context), use it.
             req_format = intent_data.get('format', 'text') # Default text
             
             if req_format == 'table':
                 return {'type': 'text', 'content': table_content, 'is_table': True}
             else:
                 return {'type': 'text', 'content': text_content}

        return {'type': 'text', 'content': "Error generando reporte."}

    def _make_graph(self, df, time_range):
        plt.figure(figsize=(10, 6))
        
        # Pivot for Multi-Bar Chart: User vs Category
        # Index: Category, Columns: User, Values: Amount
        if 'user' in df.columns and 'category' in df.columns:
            pivot = df.pivot_table(index='category', columns='user', values='amount', aggfunc='sum', fill_value=0)
            
            if pivot.empty: return None
            
            # Plot
            pivot.plot(kind='bar', figsize=(10, 6), width=0.8)
            plt.title(f'Gastos por Usuario y Categoría ({time_range})')
            plt.xlabel('Categoría')
            plt.ylabel('Total (Bs)')
            plt.xticks(rotation=45, ha='right')
            plt.legend(title='Usuario')
            plt.tight_layout()
        else:
            # Fallback simple bar
            df.groupby('category')['amount'].sum().plot(kind='bar')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        return buf
