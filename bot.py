import logging
import os
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from rembg import remove
from PIL import Image
from flask import Flask
from threading import Thread

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Создаем Flask сервер для Render
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app_flask.run(host='0.0.0.0', port=port)

async def start(update: Update, context):
    await update.message.reply_text("👋 Отправь мне фото, я удалю фон!")

async def process_photo(update: Update, context):
    try:
        await update.message.reply_text("⏳ Обрабатываю...")
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        input_image = Image.open(BytesIO(photo_bytes))
        output_image = remove(input_image)
        output_buffer = BytesIO()
        output_image.save(output_buffer, format='PNG')
        output_buffer.seek(0)
        await update.message.reply_document(document=output_buffer, filename="no_bg.png", caption="✅ Готово!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# Запускаем Flask в отдельном потоке
Thread(target=run_flask, daemon=True).start()

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, process_photo))
print("🚀 Бот запущен!")
app.run_polling()
