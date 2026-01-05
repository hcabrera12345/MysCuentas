import logging
import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from ai_handler import AIHandler
from sheets_handler import SheetsHandler
from utils import get_current_date

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize Handlers
try:
    ai_handler = AIHandler()
    sheets_handler = SheetsHandler()
    print("AI and Sheets Handlers initialized successfully.")
except Exception as e:
    print(f"CRITICAL: Failed to initialize handlers. Check credentials. {e}")
    # We continue to allow the bot to start so it doesn't crash Render immediately, 
    # but actual functionality will fail.

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Soy MysCuentas Bot. 🤖\n"
        "Envíame un audio o texto con tu gasto y lo guardaré en Sheets.\n"
        "Ejemplo: '50 bolivianos en gasolina'"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await process_input(update, user_text, is_voice=False)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Download voice file
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    file_path = f"voice_{update.message.from_user.id}.ogg"
    await voice_file.download_to_drive(file_path)
    
    await process_input(update, file_path, is_voice=True)
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)


from report_engine import ReportEngine

async def process_input(update: Update, input_data, is_voice):
    status_msg = await update.message.reply_text("⏳ Procesando...")
    
    try:
        if is_voice:
            # Voice is currently always treated as Expense for simplicity, 
            # unless we upgrade process_audio to return Intent.
            data = ai_handler.process_audio(input_data)
            if not data:
                await status_msg.edit_text("❌ No pude entender el audio. ¿Seguro que es un gasto?")
                return
            intent_type = 'EXPENSE'
            intent_data = data # Legacy format from process_audio
        else:
            # Text uses new Intent Parser
            result = ai_handler.parse_intent(input_data)
            if not result:
                 await status_msg.edit_text("❌ No entendí. Intenta de nuevo.")
                 return
            intent_type = result.get('type')
            intent_data = result.get('data')

        if intent_type == 'EXPENSE':
            # Use current date if AI didn't find one
            date = intent_data.get('date') or get_current_date()
            item = intent_data.get('item', 'Desconocido')
            amount = intent_data.get('amount', 0)
            currency = intent_data.get('currency', 'Bs')
            category = intent_data.get('category', 'Otros')
            
            # Save to Sheets
            success = sheets_handler.add_expense(date, category, item, amount, currency)
            
            if success:
                await status_msg.edit_text(
                    f"✅ **Gasto Guardado**\n"
                    f"📅 Fecha: {date}\n"
                    f"🛒 Item: {item}\n"
                    f"💰 Todo: {amount} {currency}\n"
                    f"📂 Categ: {category}"
                )
            else:
                await status_msg.edit_text("⚠️ Error al guardar en Google Sheets. Verifica la conexión.")

        elif intent_type == 'REPORT':
            records = sheets_handler.get_all_records()
            engine = ReportEngine(records)
            time_range = intent_data.get('time_range', 'all')
            query_type = intent_data.get('query_type', 'text')

            if query_type == 'graph':
                graph_buf = engine.generate_graph(time_range)
                if graph_buf:
                    await status_msg.delete()
                    await update.message.reply_photo(photo=graph_buf, caption=f"📊 Gráfico de gastos ({time_range})")
                else:
                    await status_msg.edit_text("No hay datos suficientes para el gráfico.")
            else:
                report_text = engine.generate_text_report(time_range)
                await status_msg.edit_text(report_text)
                
    except Exception as e:
        logging.error(f"Error processing input: {e}")
        await status_msg.edit_text(f"🔥 Ocurrió un error interno: {str(e)}")


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Placeholder for reporting logic
    await update.message.reply_text("🚧 Reportes en construcción...")

if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        print("Error: TELEGRAM_TOKEN not set!")
        exit(1)

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('reporte', report))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Check for Render environment
    if os.getenv("RENDER"):
        print("Starting Webhook for Render...")
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)),
            webhook_url=os.getenv("WEBHOOK_URL")  # Must be set in Render
        )
    else:
        print("Starting Polling (Local Mode)...")
        application.run_polling()
