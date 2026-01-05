import pandas as pd
import matplotlib.pyplot as plt
import io
import datetime

class ReportEngine:
    def __init__(self, data):
        """
        data: List of dicts from SheetsHandler.get_all_records()
        """
        self.df = pd.DataFrame(data)
        # Ensure correct data types
        try:
            self.df['amount'] = pd.to_numeric(self.df['amount'])
            self.df['date'] = pd.to_datetime(self.df['date'])
        except Exception as e:
            print(f"Data conversion error: {e}")

    def filter_data(self, time_range):
        if self.df.empty:
            return self.df
            
        today = datetime.datetime.now()
        if time_range == 'today':
            return self.df[self.df['date'].dt.date == today.date()]
        elif time_range == 'week':
            start_date = today - datetime.timedelta(days=7)
            return self.df[self.df['date'] >= start_date]
        elif time_range == 'month':
            return self.df[self.df['date'].dt.month == today.month]
        
        return self.df

    def generate_text_report(self, time_range='all'):
        df_filtered = self.filter_data(time_range)
        
        if df_filtered.empty:
            return "No hay datos para este periodo."
            
        total = df_filtered['amount'].sum()
        by_category = df_filtered.groupby('category')['amount'].sum().to_string()
        
        return f"📊 **Reporte ({time_range})**\n\n💰 Total: {total:.2f}\n\n📂 Por Categoría:\n{by_category}"

    def generate_graph(self, time_range='all'):
        df_filtered = self.filter_data(time_range)
        
        if df_filtered.empty:
            return None
            
        plt.figure(figsize=(10, 6))
        category_sums = df_filtered.groupby('category')['amount'].sum()
        category_sums.plot(kind='bar')
        plt.title(f'Gastos por Categoría ({time_range})')
        plt.xlabel('Categoría')
        plt.ylabel('Monto')
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        return buf
