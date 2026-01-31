import logging
import os
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from rembg import remove
from PIL import Image
from aiohttp import web

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
PORT = int(os.environ.get('PORT', 10000))

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

async def health(request):
    return web.Response(text="OK")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, process_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
    
    await app.initialize()
    await app.start()
    
    webserver = web.Application()
    webserver.router.add_get("/", health)
    webserver.router.add_get("/health", health)
    
    runner = web.AppRunner(webserver)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    print(f"🚀 Бот запущен на порту {PORT}!")
    
    await app.updater.start_polling()
    
    import asyncio
    await asyncio.Event().wait()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
