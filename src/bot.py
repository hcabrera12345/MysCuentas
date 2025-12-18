import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

# Load Env (Robust Path)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Modules
from MysCuentas.src.brain import analyze_expense
from MysCuentas.src.sheets import init_db
from MysCuentas.src.reports import generate_monthly_report

# Logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ALLOWED_IDS = [x.strip() for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()]

def check_auth(user_id):
    if not ALLOWED_IDS: return True
    return str(user_id) in ALLOWED_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not check_auth(user.id):
        await update.message.reply_text("⛔")
        return
    await update.message.reply_text(
        "👋 **Hola MysCuentas Cloud**\n"
        "Estoy listo en la nube ☁️\n\n"
        "🔹 Envía gasto (Texto/Audio)\n"
        "🔹 Usa /reporte para ver resumen"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not check_auth(user.id): return

    msg_type = "Text"
    content = ""
    file_path = None

    status = await update.message.reply_text("☁️ Procesando...")

    try:
        # 1. Get Content
        if update.message.voice:
            msg_type = "Audio"
            file_id = update.message.voice.file_id
            new_file = await context.bot.get_file(file_id)
            file_path = f"temp_{file_id}.ogg"
            await new_file.download_to_drive(file_path)
            content = file_path
        else:
            content = update.message.text

        # 2. Brain Analysis
        data = analyze_expense(content, "audio/ogg" if msg_type == "Audio" else "text/plain")

        # Cleanup
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        if not data or data.get("confidence", 0) < 0.5:
            await status.edit_text("🤷‍♂️ No entendí.")
            return

        # 3. Save to DB
        sheet = init_db()
        if sheet:
            from datetime import datetime
            now = datetime.now()
            row = [
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                user.first_name,
                data.get('amount'),
                data.get('currency'),
                data.get('category'),
                data.get('subcategory'),
                data.get('description'),
                msg_type
            ]
            sheet.append_row(row)
            
            await status.edit_text(
                f"✅ **Gasto Guardado**\n"
                f"💰 {data.get('amount')} {data.get('currency')}\n"
                f"📂 {data.get('category')} - {data.get('subcategory')}\n"
                f"📝 {data.get('description')}"
            )
        else:
            await status.edit_text("⚠️ Error de BBDD.")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await status.edit_text("❌ Error interno.")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not check_auth(user.id): return
    
    status = await update.message.reply_text("📊 Generando gráfico...")
    
    try:
        sheet = init_db()
        if not sheet:
            await status.edit_text("⚠️ Error BBDD.")
            return
            
        rows = sheet.get_all_values()
        img_buf = generate_monthly_report(rows)
        
        if img_buf:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_buf, caption="gastos por Categoría")
            await status.delete()
        else:
            await status.edit_text("📉 No hay datos suficientes.")
            
    except Exception as e:
        logger.error(f"Report Error: {e}")
        await status.edit_text("❌ Error reporte.")

if __name__ == '__main__':
    if not TOKEN:
        print("ERROR: Token missing.")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CommandHandler('reporte', report))
        app.add_handler(MessageHandler(filters.TEXT | filters.VOICE, handle_message))
        print("Bot Polling...")
        app.run_polling()
