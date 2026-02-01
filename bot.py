import logging
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import os
import requests

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.environ.get('8240254491:AAE-xIqsQB_eeZpR3uECgT0RuAWM8kRJpCM')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Отправь фото!")

async def process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("⏳ Обрабатываю...")
        
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Используем бесплатный API remove.bg (50 запросов/месяц)
        # Или используем другой метод
        
        await update.message.reply_text("✅ Фото получено!")
        
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, process_photo))
    
    logging.info("🚀 Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
