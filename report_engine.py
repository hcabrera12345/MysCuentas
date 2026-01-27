import pandas as pd
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
                self.df['date'] = pd.to_datetime(self.df['date'], dayfirst=True, errors='coerce')
                
                # Lowercase string columns for easier filtering
                if 'user' in self.df.columns:
                    self.df['user_norm'] = self.df['user'].astype(str).str.lower()
                if 'category' in self.df.columns:
                    self.df['category_norm'] = self.df['category'].astype(str).str.lower()
            except Exception as e:
                print(f"Data conversion error: {e}")

    def filter_data(self, time_range='all', filter_user=None, filter_category=None):
        if self.df.empty:
            return self.df
            
        df_filtered = self.df.copy()
        today = datetime.datetime.now()
        
        # 1. Date Filter
        if pd.api.types.is_datetime64_any_dtype(df_filtered['date']):
            # Clean time range string
            tr = str(time_range).lower().strip()
            
            if 'today' in tr or 'hoy' in tr:
                df_filtered = df_filtered[df_filtered['date'].dt.date == today.date()]
            elif 'week' in tr or 'semana' in tr:
                start_date = today - datetime.timedelta(days=7)
                df_filtered = df_filtered[df_filtered['date'] >= start_date]
            elif 'month' in tr or 'mes' in tr:
                df_filtered = df_filtered[df_filtered['date'].dt.month == today.month]
                df_filtered = df_filtered[df_filtered['date'].dt.year == today.year]
            elif 'days' in tr or 'dias' in tr:
                # Extract number from "3 days"
                try:
                    import re
                    days = int(re.search(r'\d+', tr).group())
                    start_date = today - datetime.timedelta(days=days)
                    df_filtered = df_filtered[df_filtered['date'] >= start_date]
                except:
                    pass # Fallback to all if parsing fails
        
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
        filter_category = intent_data.get('category') # AI extract 'category' as filter if it's a report

        df_subset = self.filter_data(time_range, filter_user, filter_category)
        
        if df_subset.empty:
            return {'type': 'text', 'content': f"ℹ️ No encontré registros para: {time_range} (filtro: {filter_user or 'Todos'}, cat: {filter_category or 'Todas'})."}

        # Graph Request?
        if query_type == 'graph':
            buf = self._make_graph(df_subset, time_range)
            if buf:
                # Save to temp file strictly for bot to send (avoid byte stream issues sometimes)
                path = "temp_chart.png"
                with open(path, "wb") as f:
                    f.write(buf.getbuffer())
                return {'type': 'image', 'path': path}
            else:
                 return {'type': 'text', 'content': "No hay suficientes datos para graficar."}
        
        # Default: Text Summary
        total = df_subset['amount'].sum()
        count = len(df_subset)
        
        # Breakdown by category if not filtered by category (otherwise it's redundant)
        breakdown_text = ""
        if not filter_category:
            grouped = df_subset.groupby('category')['amount'].sum().sort_values(ascending=False)
            breakdown_text = "\n📂 **Por Categoría:**\n" + "\n".join([f"• {cat}: {val:.2f}" for cat, val in grouped.items()])
        
        # Recent items snippet
        recent = df_subset.sort_values('date', ascending=False).head(5)
        recent_text = "\n\n📝 **Últimos 5:**\n" + "\n".join([f"- {row['item']} ({row['amount']})" for _, row in recent.iterrows()])

        # Construct Header
        header = f"📊 **Reporte**"
        if time_range != 'all': header += f" ({time_range})"
        if filter_user: header += f" para {filter_user.capitalize()}"
        if filter_category: header += f" en {filter_category.capitalize()}"

        msg = f"{header}\n\n💰 **Total: {total:.2f}** (en {count} registros){breakdown_text}{recent_text}"
        return {'type': 'text', 'content': msg}

    def _make_graph(self, df, time_range):
        plt.figure(figsize=(10, 6))
        category_sums = df.groupby('category')['amount'].sum()
        if category_sums.empty: return None
        
        category_sums.plot(kind='bar', color='skyblue')
        plt.title(f'Gastos ({time_range})')
        plt.xlabel('Categoría')
        plt.ylabel('Monto')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        return buf
