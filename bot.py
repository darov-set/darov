import logging
import os
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from rembg import remove
from PIL import Image
from flask import Flask, request
import asyncio

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 10000))

app_flask = Flask(__name__)
bot_app = Application.builder().token(BOT_TOKEN).build()

@app_flask.route('/')
def home():
    return "Bot is running!"

@app_flask.route('/health')
def health():
    return "OK", 200

@app_flask.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, bot_app.bot)
    asyncio.run(bot_app.process_update(update))
    return "OK"

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

async def handle_document(update: Update, context):
    document = update.message.document
    if not document.mime_type or not document.mime_type.startswith('image/'):
        await update.message.reply_text("⚠️ Отправьте изображение")
        return
    try:
        await update.message.reply_text("⏳ Обрабатываю...")
        doc_file = await document.get_file()
        doc_bytes = await doc_file.download_as_bytearray()
        input_image = Image.open(BytesIO(doc_bytes))
        if input_image.mode in ('RGBA', 'LA', 'P'):
            input_image = input_image.convert('RGB')
        output_image = remove(input_image)
        output_buffer = BytesIO()
        output_image.save(output_buffer, format='PNG')
        output_buffer.seek(0)
        original_name = document.file_name or "image"
        new_filename = f"no_bg_{original_name.rsplit('.', 1)[0]}.png"
        await update.message.reply_document(document=output_buffer, filename=new_filename, caption="✅ Готово!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.PHOTO, process_photo))
bot_app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))

async def setup_webhook():
    webhook_url = os.environ.get('RENDER_EXTERNAL_URL')
    if webhook_url:
        await bot_app.bot.set_webhook(url=f"{webhook_url}/{BOT_TOKEN}")
        print(f"Webhook set to {webhook_url}/{BOT_TOKEN}")
    await bot_app.initialize()

asyncio.run(setup_webhook())

print(f"🚀 Бот запущен на порту {PORT}!")
app_flask.run(host='0.0.0.0', port=PORT)
