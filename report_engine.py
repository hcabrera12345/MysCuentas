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
        # Rename map: Spanish -> Internal English
        rename_map = {
            'Fecha': 'date', 
            'Categoría': 'category', 
            'Item': 'item', 
            'Monto': 'amount', 
            'Moneda': 'currency',
            'Usuario': 'user'
        }
        self.df = self.raw_df.rename(columns=rename_map)
        
        # Normalize Data Types
        if not self.df.empty:
            try:
                # Force numeric, coercion errors become NaN (handle gracefully?)
                self.df['amount'] = pd.to_numeric(self.df['amount'], errors='coerce').fillna(0)
                self.df['date'] = pd.to_datetime(self.df['date'], errors='coerce')
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
            if time_range == 'today':
                df_filtered = df_filtered[df_filtered['date'].dt.date == today.date()]
            elif time_range == 'week':
                start_date = today - datetime.timedelta(days=7)
                df_filtered = df_filtered[df_filtered['date'] >= start_date]
            elif time_range == 'month':
                df_filtered = df_filtered[df_filtered['date'].dt.month == today.month]
                df_filtered = df_filtered[df_filtered['date'].dt.year == today.year]
        
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
