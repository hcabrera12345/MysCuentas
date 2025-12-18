import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import io
import logging

logger = logging.getLogger(__name__)

def generate_monthly_report(data_rows):
    """
    Generates a Pie Chart for Fixed vs Variable expenses.
    data_rows: List of lists (from Sheets).
    Returns: BytesIO object of the image.
    """
    try:
        if not data_rows or len(data_rows) < 2:
            return None

        # Convert to DataFrame
        headers = data_rows[0]
        data = data_rows[1:]
        df = pd.DataFrame(data, columns=headers)
        
        # Ensure numeric
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce')
        df = df.dropna(subset=['Monto'])

        # Group by Category (Fixed/Variable)
        summary = df.groupby('Categoría')['Monto'].sum().reset_index()

        if summary.empty:
            return None

        # Plot
        plt.figure(figsize=(6, 6))
        sns.set_style("whitegrid")
        plt.pie(summary['Monto'], labels=summary['Categoría'], autopct='%1.1f%%', colors=sns.color_palette("pastel"))
        plt.title('Gastos por Categoría')
        
        # Save to Bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        return buf

    except Exception as e:
        logger.error(f"Report Error: {e}")
        return None
