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

class ExpenseBot:
    def __init__(self):
        self.tokenizer = os.getenv("TELEGRAM_TOKEN")
        self.app = ApplicationBuilder().token(self.tokenizer).build()
        
        # Initialize Handlers
        try:
            self.ai = AIHandler()
            self.sheets = SheetsHandler()
            
            # Load Categories from Sheet
            print("Loading categories...")
            self.categories = self.sheets.get_categories()
            print(f"Loaded config: {self.categories}")
            
        except Exception as e:
            print(f"CRITICAL ERROR INIT: {e}")
            raise e

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("👋 ¡Hola! Soy MysCuentas.\n\n📝 Registra gastos escribiendo o por audio.\n📊 Pídeme reportes.\n🔄 Usa /reload para actualizar categorías desde el Sheet.")

    async def reload_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Forces a refresh of categories from Google Sheets."""
        try:
            self.categories = self.sheets.get_categories()
            await update.message.reply_text(f"✅ Categorías actualizadas: {len(self.categories)} encontradas.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error actualizando: {e}")

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_name = update.effective_user.first_name
        await self.process_input(update, update.message.text, is_voice=False, user_name=user_name)

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        file = await context.bot.get_file(update.message.voice.file_id)
        file_path = f"voice_files/file_{update.message.message_id}.oga"
        os.makedirs("voice_files", exist_ok=True)
        await file.download_to_drive(file_path)
        
        user_name = update.effective_user.first_name
        await self.process_input(update, file_path, is_voice=True, user_name=user_name)
        
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)

    async def process_input(self, update: Update, input_data: str, is_voice: bool, user_name: str):
        status_msg = await update.message.reply_text("🤔 Procesando...")
        try:
            ai_handler = self.ai
            sheets_handler = self.sheets
            
            if is_voice:
                # Voice currently treated as Expense
                data = ai_handler.process_audio(input_data, categories=self.categories)
                if not data or "error" in data:
                    err = data.get("error", "Unknown Error") if data else "None Result"
                    await status_msg.edit_text(f"⚠️ Error procesando audio: {err}")
                    return
                intent_type = 'EXPENSE'
                intent_data = data 
            else:
                # Text input
                intent = ai_handler.parse_intent(input_data, categories=self.categories)
                if not intent or "error" in intent:
                    err = intent.get("error", "Unknown Error") if intent else "None Result"
                    await status_msg.edit_text(f"⚠️ Error procesando texto: {err}")
                    return
                
                intent_type = intent.get('type')
                intent_data = intent.get('data')

            print(f"DEBUG: Intent Type: {intent_type}, Data: {intent_data}") 

            if intent_type == 'REPORT':
                await status_msg.edit_text("📊 Generando reporte...")
                # Report logic here (passing user_name? maybe for filtering later)
                # For now standard report
                # Actually, let's keep existing report logic or assume report_engine integration
                from report_engine import ReportEngine
                engine = ReportEngine(sheets_handler.sheet)
                result = engine.generate_report(intent_data)
                
                if result['type'] == 'text':
                    await status_msg.edit_text(result['content'])
                elif result['type'] == 'image':
                    await status_msg.delete()
                    await update.message.reply_photo(photo=open(result['path'], 'rb'), caption="Aquí tienes tu gráfico 📈")
                
            elif intent_type == 'EXPENSE':
                item = intent_data.get('item', 'Desconocido')
                amount = intent_data.get('amount', 0)
                currency = intent_data.get('currency', 'Bs')
                category = intent_data.get('category', 'Otros')
                date = intent_data.get('date') or get_current_date()
                
                success = sheets_handler.add_expense(date, category, item, amount, currency, user_name)
                
                if success:
                    await status_msg.edit_text(
                        f"✅ **Gasto Guardado**\n"
                        f"👤 Usuario: {user_name}\n"
                        f"📅 Fecha: {date}\n"
                        f"🛒 Item: {item}\n"
                        f"💰 Todo: {amount} {currency}\n"
                        f"📂 Categ: {category}"
                    )
                else:
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
