import logging
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
            
            # Load Whitelist
            allowed_users_env = os.getenv("ALLOWED_USERS", "")
            self.allowed_users = [
                int(uid.strip()) 
                for uid in allowed_users_env.split(",") 
                if uid.strip().isdigit()
            ]
            if not self.allowed_users:
                print("⚠️ WARNING: ALLOWED_USERS is empty. Bot is public!")
            else:
                print(f"🔒 Security Active. Allowed IDs: {self.allowed_users}")

        except Exception as e:
            print(f"CRITICAL ERROR INIT: {e}")
            raise e

    async def check_auth(self, update: Update) -> bool:
        """Returns True if user is authorized, False otherwise."""
        if not self.allowed_users:
            return True # Public mode
        
        user_id = update.effective_user.id
        if user_id in self.allowed_users:
            return True
        
        # Unauthorized
        print(f"⛔ Unauthorized access attempt by ID: {user_id} ({update.effective_user.first_name})")
        await update.message.reply_text(f"⛔ **Acceso Denegado**\nTu ID de Telegram es: `{user_id}`\n\nContacta al administrador para que te agregue.")
        return False

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        
        await update.message.reply_text("👋 ¡Hola! Soy MysCuentas.\n\n📝 Registra gastos escribiendo o por audio.\n📊 Pídeme reportes.\n🔄 Usa /reload para actualizar categorías desde el Sheet.")

    async def reload_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        
        """Forces a refresh of categories from Google Sheets."""
        try:
            self.categories = self.sheets.get_categories()
            await update.message.reply_text(f"✅ Categorías actualizadas: {len(self.categories)} encontradas.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error actualizando: {e}")

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        
        user_name = update.effective_user.first_name
        await self.process_input(update, context, update.message.text, is_voice=False, user_name=user_name)

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        
        file = await context.bot.get_file(update.message.voice.file_id)
        file_path = f"voice_files/file_{update.message.message_id}.oga"
        os.makedirs("voice_files", exist_ok=True)
        await file.download_to_drive(file_path)
        
        user_name = update.effective_user.first_name
        await self.process_input(update, context, file_path, is_voice=True, user_name=user_name)
        
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)

    async def process_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, input_data: str, is_voice: bool, user_name: str):
        # Auth checked by callers
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
                # Preguntar formato si no se especificó o forzar siempre la pregunta para mejor UX
                # Guardamos los datos del reporte en el contexto del usuario para usarlos cuando presione el botón
                context.user_data['report_request'] = intent_data
                
                keyboard = [
                    [
                        InlineKeyboardButton("📝 Texto", callback_data='rep_text'),
                        InlineKeyboardButton("📉 Gráfico", callback_data='rep_graph'),
                        InlineKeyboardButton("📋 Tabla", callback_data='rep_table')
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await status_msg.edit_text("📊 ¿Cómo quieres ver el reporte?", reply_markup=reply_markup)
            
            elif intent_type == 'DELETE':
                deleted = sheets_handler.delete_last_entry(user_name)
                if deleted:
                    await status_msg.edit_text(f"🗑️ **Eliminado con éxito**\nRegistro: {deleted}")
                else:
                    await status_msg.edit_text("🤷‍♂️ No encontré ningún gasto reciente tuyo para borrar.")

            elif intent_type == 'EXPENSE':
                # Handle List of expenses (new feature) or single dict
                expenses = intent_data if isinstance(intent_data, list) else [intent_data]
                
                results = []
                for exp in expenses:
                    item = exp.get('item', 'Desconocido')
                    amount = exp.get('amount', 0)
                    currency = exp.get('currency', 'Bs')
                    category = exp.get('category', 'Otros')
                    date = exp.get('date') or get_current_date()
                    
                    if sheets_handler.add_expense(date, category, item, amount, currency, user_name):
                        # Requested Format:
                        # ✅ **Gasto Guardado**
                        # 👤 Usuario: Hernan
                        # 📅 Fecha: 2026-01-25
                        # 🛒 Item: cerveza
                        # 💰 Todo: 90 Bs
                        # 📂 Categ: ENTRETENIMIENTO
                        msg = (
                            f"✅ **Gasto Guardado**\n"
                            f"👤 Usuario: {user_name}\n"
                            f"📅 Fecha: {date}\n"
                            f"🛒 Item: {item}\n"
                            f"💰 Todo: {amount} {currency}\n"
                            f"📂 Categ: {category.upper()}"
                        )
                        results.append(msg)
                    else:
                        results.append(f"❌ Error guardando: {item}")
                
                await status_msg.edit_text("\n\n".join(results), parse_mode='Markdown')
            
            else:
                 await status_msg.edit_text("❌ Tipo de solicitud desconocida.")
                
        except Exception as e:
            logging.error(f"Error processing input: {e}")
            await status_msg.edit_text(f"🔥 Ocurrió un error interno: {str(e)}")

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update): return
        
        query = update.callback_query
        await query.answer() # Acknowledge click
        
        data = query.data
        if not data.startswith('rep_'): return
        
        # Recuperar los filtros guardados
        report_data = context.user_data.get('report_request', {})
        
        # Override query type based on button click
        if data == 'rep_graph':
            report_data['query_type'] = 'graph'
        elif data == 'rep_table':
            report_data['query_type'] = 'list'
            report_data['format'] = 'table'
        else:
            report_data['query_type'] = 'list' 
            report_data['format'] = 'text'
            
        await query.edit_message_text(f"📊 Generando reporte ({data.split('_')[1]})...")
        
        try:
             # Fetch fresh records from Sheet
            records = self.sheets.get_all_records()
            from report_engine import ReportEngine
            engine = ReportEngine(records)
            
            result = engine.generate_report(report_data)
            
            if result['type'] == 'text':
                msg = result['content']
                if result.get('is_table'):
                    # Convert content to code block for "Table" look
                    msg = f"```\n{msg}\n```"
                await query.edit_message_text(msg, parse_mode='Markdown')
                
            elif result['type'] == 'image':
                await query.delete_message()
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=open(result['path'], 'rb'), caption="Aquí tienes tu gráfico 📈")
                
        except Exception as e:
             await query.edit_message_text(f"⚠️ Error generando reporte: {e}")

if __name__ == '__main__':
    try:
        # Instantiate the bot class
        bot = ExpenseBot()
        
        # Register Handlers from the bot instance
        bot.app.add_handler(CommandHandler("start", bot.start))
        bot.app.add_handler(CommandHandler("reload", bot.reload_categories))
        bot.app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), bot.handle_text))
        bot.app.add_handler(MessageHandler(filters.VOICE, bot.handle_voice))
        bot.app.add_handler(CallbackQueryHandler(bot.button_handler))

        # Check for Render environment
        if os.getenv("RENDER"):
            print("Starting Webhook for Render...")
            bot.app.run_webhook(
                listen="0.0.0.0",
                port=int(os.environ.get("PORT", 8080)),
                webhook_url=os.getenv("WEBHOOK_URL")
            )
        else:
            print("Starting Polling (Local Mode)...")
            bot.app.run_polling()
            
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        exit(1)
