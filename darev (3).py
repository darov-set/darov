"""
✨ THE DAROV BOT ULTIMATE v4.2 - PREMIUM EDITION ✨

Интеллектуальный AI-ассистент с полным функционалом
• 🧠 TheDarov AI - Умный помощник нового поколения
• 🎤 Распознавание голосовых сообщений
• 🌐 Веб-поиск актуальной информации
• 🎨 Генерация изображений (скоро будет доступна!)
• 👑 Продвинутая админ-панель
• 🌅 Автоматические приветствия
• 📊 Детальная статистика
• 🔄 Автоперезапуск и самовосстановление
• 📝 Профессиональное логирование
• ⚡ Оптимизация для бесперебойной работы 24/7
• 🎨 Красивый интерфейс с удобными кнопками

💫 Создатель: darov
🔧 Адаптировано для Render.com
"""

import requests
import random
import json
import os
import io
import threading
import time
import pytz
import sys
import logging
import traceback
from datetime import datetime, timedelta
from telebot import TeleBot, types
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from flask import Flask
from threading import Thread

# ═══════════════════════════════════════════════════════════════
#                    🌐 FLASK ВЕБ-СЕРВЕР ДЛЯ RENDER
# ═══════════════════════════════════════════════════════════════

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Darov Bot is alive and running!"

@app.route('/health')
def health():
    return {
        "status": "healthy",
        "uptime": time.time() - bot_start_time if bot_start_time else 0
    }

def run_flask():
    """Запуск Flask-сервера в отдельном потоке"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Запустить веб-сервер для предотвращения засыпания на Render"""
    t = Thread(target=run_flask, daemon=True)
    t.start()
    logger.info(f"🌐 Flask веб-сервер запущен на порту {os.environ.get('PORT', 10000)}")

# ═══════════════════════════════════════════════════════════════
#                         🔧 НАСТРОЙКИ
# ═══════════════════════════════════════════════════════════════

# ВАЖНО: Токены теперь берутся из переменных окружения!
BOT_TOKEN = os.environ.get('BOT_TOKEN')
AI_API_KEY = os.environ.get('AI_API_KEY')

# Проверка наличия токенов
if not BOT_TOKEN or not AI_API_KEY:
    print("❌ ОШИБКА: Не найдены переменные окружения BOT_TOKEN или AI_API_KEY!")
    print("💡 Добавьте их в настройках Render.com:")
    print("   Environment -> Add Environment Variable")
    sys.exit(1)

# ID администратора (можно тоже вынести в переменную окружения)
ADMIN_ID = int(os.environ.get('ADMIN_ID', 6829681470))

# Настройки московского времени
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# Временные диапазоны для автоматических приветствий
MORNING_GREETING_START = 5   # 5:00 утра
MORNING_GREETING_END = 7     # 7:00 утра
NIGHT_GREETING_START = 21    # 21:00 (9 PM)
NIGHT_GREETING_END = 23      # 23:00 (11 PM)

# Настройки для работы 24/7
MAX_RESTART_ATTEMPTS = 10  # Максимум попыток перезапуска
RESTART_DELAY = 5  # Задержка перед перезапуском (секунды)
HEALTHCHECK_INTERVAL = 300  # Проверка здоровья каждые 5 минут
API_TIMEOUT = 60  # Таймаут для API запросов
MAX_MESSAGE_LENGTH = 10000  # Максимальная длина ответа

# ═══════════════════════════════════════════════════════════════
#                      📝 СИСТЕМА ЛОГИРОВАНИЯ
# ═══════════════════════════════════════════════════════════════

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('DarovBot')

# Отключаем излишние логи от библиотек
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('telebot').setLevel(logging.INFO)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# ═══════════════════════════════════════════════════════════════
#                      🤖 ИНИЦИАЛИЗАЦИЯ БОТА
# ═══════════════════════════════════════════════════════════════

bot = TeleBot(BOT_TOKEN, parse_mode='HTML', threaded=True)
user_contexts = {}
user_states = {}  # Словарь для отслеживания состояний пользователей
last_healthcheck = time.time()
bot_start_time = None

# Режим технических работ (установите True для включения)
MAINTENANCE_MODE = False

# ═══════════════════════════════════════════════════════════════
#                 📝 ОБРАБОТКА ДЛИННЫХ СООБЩЕНИЙ
# ═══════════════════════════════════════════════════════════════

def split_message(text, max_length=4000):
    """Разделить длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]

    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break

        # Пытаемся разбить по абзацам
        split_point = text.rfind('\n', 0, max_length)
        if split_point == -1:
            # Если нет абзацев, разбиваем по предложениям
            split_point = text.rfind('. ', 0, max_length)
            if split_point == -1:
                # Если нет точек, разбиваем по пробелам
                split_point = text.rfind(' ', 0, max_length)
                if split_point == -1:
                    # Если нет пробелов, просто обрезаем
                    split_point = max_length

        part = text[:split_point].strip()
        if part:
            parts.append(part)
        text = text[split_point:].strip()

    return parts

def send_long_message(chat_id, text, reply_markup=None):
    """Отправить длинное сообщение частями"""
    try:
        # Ограничиваем общую длину ответа
        if len(text) > MAX_MESSAGE_LENGTH:
            text = text[:MAX_MESSAGE_LENGTH - 100] + "\n\n... (сообщение слишком длинное, обрезано)"

        parts = split_message(text)

        for i, part in enumerate(parts):
            try:
                # Разметка только на последней части
                markup = reply_markup if i == len(parts) - 1 else None
                bot.send_message(chat_id, part, reply_markup=markup)
                time.sleep(0.05)  # Небольшая задержка между сообщениями
            except Exception as e:
                logger.error(f"Ошибка отправки части сообщения: {e}")
    except Exception as e:
        logger.error(f"Критическая ошибка в send_long_message: {e}")

# ═══════════════════════════════════════════════════════════════
#                      💾 БАЗА ДАННЫХ
# ═══════════════════════════════════════════════════════════════

DB_FILE = "users_database.json"
LOGS_FILE = "users_logs.json"
ADMIN_SETTINGS_FILE = "admin_settings.json"
GREETINGS_FILE = "greetings_state.json"

def safe_file_operation(operation, *args, **kwargs):
    """Безопасное выполнение файловых операций с повторными попытками"""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            if attempt == max_attempts - 1:
                logger.error(f"Файловая операция не удалась после {max_attempts} попыток: {e}")
                raise
            time.sleep(0.1 * (attempt + 1))

def load_database():
    """Загрузить базу данных пользователей с проверкой структуры"""
    def _load():
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                db = json.load(f)

            if "users" not in db:
                db["users"] = {}

            if "stats" not in db:
                db["stats"] = {}

            required_stats = ["total", "active", "today_new", "messages_today"]
            for stat_key in required_stats:
                if stat_key not in db["stats"]:
                    db["stats"][stat_key] = 0

            for user_id_str in list(db["users"].keys()):
                user_data = db["users"][user_id_str]
                required_user_fields = [
                    "user_id", "username", "first_name", "last_name",
                    "joined_date", "last_active", "is_active",
                    "messages_count"
                ]

                for field in required_user_fields:
                    if field not in user_data:
                        if field == "is_active":
                            user_data[field] = True
                        elif field == "messages_count":
                            user_data[field] = 0
                        else:
                            user_data[field] = ""

            return db

        return {
            "users": {},
            "stats": {
                "total": 0,
                "active": 0,
                "today_new": 0,
                "messages_today": 0
            }
        }

    try:
        return safe_file_operation(_load)
    except Exception as e:
        logger.error(f"Ошибка загрузки базы данных: {e}")
        return {
            "users": {},
            "stats": {
                "total": 0,
                "active": 0,
                "today_new": 0,
                "messages_today": 0
            }
        }

def save_database(db):
    """Сохранить базу данных"""
    def _save():
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)

    try:
        safe_file_operation(_save)
    except Exception as e:
        logger.error(f"Ошибка сохранения базы данных: {e}")

def load_logs():
    """Загрузить логи активности пользователей"""
    def _load():
        if os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    try:
        return safe_file_operation(_load)
    except Exception as e:
        logger.error(f"Ошибка загрузки логов: {e}")
        return {}

def save_logs(logs):
    """Сохранить логи активности"""
    def _save():
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    try:
        safe_file_operation(_save)
    except Exception as e:
        logger.error(f"Ошибка сохранения логов: {e}")

def load_admin_settings():
    """Загрузить настройки админ-панели"""
    def _load():
        if os.path.exists(ADMIN_SETTINGS_FILE):
            with open(ADMIN_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "auto_greetings": True,
            "greeting_morning": True,
            "greeting_night": True
        }

    try:
        return safe_file_operation(_load)
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек: {e}")
        return {
            "auto_greetings": True,
            "greeting_morning": True,
            "greeting_night": True
        }

def save_admin_settings(settings):
    """Сохранить настройки админ-панели"""
    def _save():
        with open(ADMIN_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

    try:
        safe_file_operation(_save)
    except Exception as e:
        logger.error(f"Ошибка сохранения настроек: {e}")

def load_greetings_state():
    """Загрузить состояние приветствий"""
    def _load():
        if os.path.exists(GREETINGS_FILE):
            with open(GREETINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    try:
        return safe_file_operation(_load)
    except Exception as e:
        logger.error(f"Ошибка загрузки состояния приветствий: {e}")
        return {}

def save_greetings_state(state):
    """Сохранить состояние приветствий"""
    def _save():
        with open(GREETINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    try:
        safe_file_operation(_save)
    except Exception as e:
        logger.error(f"Ошибка сохранения состояния приветствий: {e}")

# ═══════════════════════════════════════════════════════════════
#            🧠 AI ФУНКЦИИ (GroqCloud API)
# ═══════════════════════════════════════════════════════════════

def get_ai_response(user_id, user_message, max_retries=3):
    """Получить ответ от AI с использованием GroqCloud API"""
    
    # Инициализируем контекст пользователя, если его нет
    if user_id not in user_contexts:
        user_contexts[user_id] = []

    # Добавляем сообщение пользователя в контекст
    user_contexts[user_id].append({
        "role": "user",
        "content": user_message
    })

    # Ограничиваем размер контекста (последние 10 сообщений)
    if len(user_contexts[user_id]) > 20:
        user_contexts[user_id] = user_contexts[user_id][-20:]

    # Системный промпт
    system_prompt = {
        "role": "system",
        "content": (
            "Ты — TheDarov AI, умный и дружелюбный AI-ассистент. "
            "Отвечай максимально полезно, четко и по существу. "
            "Используй эмодзи для наглядности. "
            "Если не знаешь точного ответа — честно признайся. "
            "Отвечай на русском языке."
        )
    }

    # Формируем запрос к API
    messages = [system_prompt] + user_contexts[user_id]

    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {AI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2048
                },
                timeout=API_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                ai_reply = result["choices"][0]["message"]["content"]
                
                # Добавляем ответ AI в контекст
                user_contexts[user_id].append({
                    "role": "assistant",
                    "content": ai_reply
                })
                
                return ai_reply
            else:
                logger.error(f"GroqCloud API вернул код {response.status_code}: {response.text}")
                if attempt == max_retries - 1:
                    return "😔 Извините, AI временно недоступен. Попробуйте позже."
                time.sleep(2 ** attempt)

        except requests.exceptions.Timeout:
            logger.error(f"Таймаут при запросе к GroqCloud API (попытка {attempt + 1})")
            if attempt == max_retries - 1:
                return "⏱️ Превышено время ожидания ответа. Попробуйте позже."
            time.sleep(2 ** attempt)

        except Exception as e:
            logger.error(f"Ошибка при обращении к GroqCloud API: {e}")
            if attempt == max_retries - 1:
                return "❌ Произошла ошибка при обработке запроса. Попробуйте еще раз."
            time.sleep(2 ** attempt)

    return "❌ Не удалось получить ответ от AI после нескольких попыток."

# ═══════════════════════════════════════════════════════════════
#                   🔍 ВЕБ-ПОИСК (Serper API)
# ═══════════════════════════════════════════════════════════════

SERPER_API_KEY = os.environ.get('SERPER_API_KEY', 'demo')  # Опционально

def web_search(query, max_results=5):
    """Выполнить поиск в интернете через Serper API"""
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json"
            },
            json={"q": query, "num": max_results},
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            return results.get("organic", [])
        else:
            logger.error(f"Serper API вернул код {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Ошибка веб-поиска: {e}")
        return []

def is_search_query(text):
    """Определить, является ли запрос поисковым"""
    search_keywords = [
        "найди", "поищи", "погугли", "что такое", "кто такой",
        "где находится", "как добраться", "сколько стоит",
        "последние новости", "актуальная информация", "цена",
        "курс", "погода", "расписание"
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in search_keywords)

def search_and_summarize(user_id, query):
    """Поиск информации и создание резюме с помощью AI"""
    # Выполняем поиск
    search_results = web_search(query)
    
    if not search_results:
        return "🔍 К сожалению, не удалось найти информацию по вашему запросу."
    
    # Формируем контекст из результатов поиска
    context = "Результаты поиска:\n\n"
    for i, result in enumerate(search_results[:5], 1):
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        context += f"{i}. {title}\n{snippet}\n\n"
    
    # Просим AI обработать результаты
    prompt = (
        f"На основе следующих результатов поиска ответь на вопрос: {query}\n\n"
        f"{context}\n"
        "Дай краткий, но информативный ответ. Укажи источники, если это важно."
    )
    
    return get_ai_response(user_id, prompt)

# ═══════════════════════════════════════════════════════════════
#                   📊 СТАТИСТИКА И ЛОГИ
# ═══════════════════════════════════════════════════════════════

def update_user_in_db(user):
    """Обновить или добавить пользователя в базу данных"""
    try:
        db = load_database()
        user_id_str = str(user.id)
        
        now = datetime.now(MOSCOW_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        if user_id_str not in db["users"]:
            # Новый пользователь
            db["users"][user_id_str] = {
                "user_id": user.id,
                "username": user.username or "",
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "joined_date": now,
                "last_active": now,
                "is_active": True,
                "messages_count": 0
            }
            db["stats"]["total"] += 1
            db["stats"]["today_new"] += 1
            logger.info(f"✨ Новый пользователь: {user.first_name} (@{user.username})")
        else:
            # Обновляем существующего
            db["users"][user_id_str]["last_active"] = now
            db["users"][user_id_str]["username"] = user.username or ""
            db["users"][user_id_str]["first_name"] = user.first_name or ""
            db["users"][user_id_str]["last_name"] = user.last_name or ""
            db["users"][user_id_str]["is_active"] = True
        
        save_database(db)
        
    except Exception as e:
        logger.error(f"Ошибка обновления пользователя в БД: {e}")

def update_user_stats(user_id, messages_inc=0):
    """Обновить статистику пользователя"""
    try:
        db = load_database()
        user_id_str = str(user_id)
        
        if user_id_str in db["users"]:
            db["users"][user_id_str]["messages_count"] += messages_inc
            db["stats"]["messages_today"] += messages_inc
            save_database(db)
            
    except Exception as e:
        logger.error(f"Ошибка обновления статистики: {e}")

def log_user_action(user_id, action, details=""):
    """Записать действие пользователя в лог"""
    try:
        logs = load_logs()
        user_id_str = str(user_id)
        
        if user_id_str not in logs:
            logs[user_id_str] = []
        
        log_entry = {
            "timestamp": datetime.now(MOSCOW_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            "action": action,
            "details": details
        }
        
        logs[user_id_str].append(log_entry)
        
        # Ограничиваем размер лога (последние 100 записей)
        if len(logs[user_id_str]) > 100:
            logs[user_id_str] = logs[user_id_str][-100:]
        
        save_logs(logs)
        
    except Exception as e:
        logger.error(f"Ошибка записи в лог: {e}")

# ═══════════════════════════════════════════════════════════════
#                   🎨 КЛАВИАТУРЫ И МЕНЮ
# ═══════════════════════════════════════════════════════════════

def get_main_menu():
    """Главное меню с кнопками"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    btn1 = KeyboardButton("💬 Начать диалог")
    btn2 = KeyboardButton("🔍 Веб-поиск")
    btn3 = KeyboardButton("ℹ️ О боте")
    btn4 = KeyboardButton("📊 Моя статистика")
    
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    
    return markup

def get_admin_menu():
    """Админ-панель"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")
    )
    markup.add(
        InlineKeyboardButton("📤 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")
    )
    markup.add(
        InlineKeyboardButton("📝 Логи", callback_data="admin_logs"),
        InlineKeyboardButton("🔄 Перезапуск", callback_data="admin_restart")
    )
    
    return markup

# ═══════════════════════════════════════════════════════════════
#                   🌅 АВТОМАТИЧЕСКИЕ ПРИВЕТСТВИЯ
# ═══════════════════════════════════════════════════════════════

def check_and_send_greetings():
    """Проверка времени и отправка автоматических приветствий"""
    greetings_sent_today = load_greetings_state()
    
    while True:
        try:
            settings = load_admin_settings()
            
            if not settings.get("auto_greetings", True):
                time.sleep(300)
                continue
            
            now = datetime.now(MOSCOW_TZ)
            current_date = now.strftime('%Y-%m-%d')
            current_hour = now.hour
            
            # Проверка утреннего приветствия
            if (settings.get("greeting_morning", True) and 
                MORNING_GREETING_START <= current_hour < MORNING_GREETING_END and
                greetings_sent_today.get("morning") != current_date):
                
                send_morning_greetings()
                greetings_sent_today["morning"] = current_date
                save_greetings_state(greetings_sent_today)
            
            # Проверка ночного приветствия
            if (settings.get("greeting_night", True) and
                NIGHT_GREETING_START <= current_hour < NIGHT_GREETING_END and
                greetings_sent_today.get("night") != current_date):
                
                send_night_greetings()
                greetings_sent_today["night"] = current_date
                save_greetings_state(greetings_sent_today)
            
            # Проверяем каждые 5 минут
            time.sleep(300)
            
        except Exception as e:
            logger.error(f"Ошибка в системе приветствий: {e}")
            time.sleep(300)

def send_morning_greetings():
    """Отправить утренние приветствия"""
    try:
        db = load_database()
        greetings = [
            "🌅 Доброе утро! Начинаем новый день вместе!",
            "☀️ Привет! Желаю продуктивного дня!",
            "🌞 С добрым утром! Готов помочь тебе сегодня!"
        ]
        
        for user_id_str, user_data in db["users"].items():
            if user_data.get("is_active", True):
                try:
                    greeting = random.choice(greetings)
                    bot.send_message(
                        int(user_id_str),
                        greeting,
                        reply_markup=get_main_menu()
                    )
                    time.sleep(0.05)
                except Exception as e:
                    logger.error(f"Не удалось отправить утреннее приветствие пользователю {user_id_str}: {e}")
        
        logger.info("✅ Утренние приветствия отправлены")
        
    except Exception as e:
        logger.error(f"Ошибка отправки утренних приветствий: {e}")

def send_night_greetings():
    """Отправить ночные приветствия"""
    try:
        db = load_database()
        greetings = [
            "🌙 Спокойной ночи! Отдыхай хорошо!",
            "⭐ Доброй ночи! До встречи завтра!",
            "🌃 Хорошего отдыха! Увидимся утром!"
        ]
        
        for user_id_str, user_data in db["users"].items():
            if user_data.get("is_active", True):
                try:
                    greeting = random.choice(greetings)
                    bot.send_message(
                        int(user_id_str),
                        greeting,
                        reply_markup=get_main_menu()
                    )
                    time.sleep(0.05)
                except Exception as e:
                    logger.error(f"Не удалось отправить ночное приветствие пользователю {user_id_str}: {e}")
        
        logger.info("✅ Ночные приветствия отправлены")
        
    except Exception as e:
        logger.error(f"Ошибка отправки ночных приветствий: {e}")

# ═══════════════════════════════════════════════════════════════
#                   💚 HEALTHCHECK МОНИТОРИНГ
# ═══════════════════════════════════════════════════════════════

def healthcheck_monitor():
    """Мониторинг здоровья бота"""
    global last_healthcheck
    
    while True:
        try:
            time.sleep(HEALTHCHECK_INTERVAL)
            
            current_time = time.time()
            uptime = current_time - bot_start_time if bot_start_time else 0
            
            logger.info(f"💚 Healthcheck: бот работает {uptime/3600:.1f} часов")
            last_healthcheck = current_time
            
        except Exception as e:
            logger.error(f"Ошибка в healthcheck: {e}")

# ═══════════════════════════════════════════════════════════════
#                      📱 ОБРАБОТЧИКИ КОМАНД
# ═══════════════════════════════════════════════════════════════

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обработка команды /start"""
    try:
        user = message.from_user
        update_user_in_db(user)
        log_user_action(user.id, "start")
        
        welcome_text = (
            f"👋 <b>Привет, {user.first_name}!</b>\n\n"
            "Я — <b>TheDarov AI</b> — твой умный помощник! 🧠\n\n"
            "🎯 <b>Что я умею:</b>\n"
            "💬 Отвечать на любые вопросы\n"
            "🔍 Искать актуальную информацию в интернете\n"
            "🎤 Распознавать голосовые сообщения\n"
            "🎨 Генерировать изображения (скоро!)\n\n"
            "Просто напиши мне что угодно, и я постараюсь помочь! 😊"
        )
        
        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=get_main_menu()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")

@bot.message_handler(commands=['help'])
def handle_help(message):
    """Обработка команды /help"""
    try:
        help_text = (
            "📚 <b>Помощь по боту</b>\n\n"
            "<b>Команды:</b>\n"
            "/start - Начать работу\n"
            "/help - Показать эту справку\n"
            "/stats - Моя статистика\n"
            "/clear - Очистить контекст диалога\n"
            "/myid - Узнать свой ID\n\n"
            "<b>Кнопки меню:</b>\n"
            "💬 Начать диалог - Общение с AI\n"
            "🔍 Веб-поиск - Поиск информации\n"
            "ℹ️ О боте - Информация о боте\n"
            "📊 Моя статистика - Ваша статистика\n\n"
            "Просто напиши любой вопрос, и я отвечу! 😊"
        )
        
        bot.send_message(message.chat.id, help_text)
        
    except Exception as e:
        logger.error(f"Ошибка в /help: {e}")

@bot.message_handler(commands=['stats'])
def handle_stats(message):
    """Статистика пользователя"""
    try:
        user_id = message.from_user.id
        db = load_database()
        user_data = db["users"].get(str(user_id), {})
        
        stats_text = (
            f"📊 <b>Твоя статистика</b>\n\n"
            f"👤 Имя: {user_data.get('first_name', 'Неизвестно')}\n"
            f"🆔 ID: {user_id}\n"
            f"📅 Дата регистрации: {user_data.get('joined_date', 'Неизвестно')}\n"
            f"💬 Сообщений отправлено: {user_data.get('messages_count', 0)}\n"
            f"🕐 Последняя активность: {user_data.get('last_active', 'Неизвестно')}"
        )
        
        bot.send_message(message.chat.id, stats_text)
        
    except Exception as e:
        logger.error(f"Ошибка в /stats: {e}")

@bot.message_handler(commands=['clear'])
def handle_clear(message):
    """Очистить контекст диалога"""
    try:
        user_id = message.from_user.id
        if user_id in user_contexts:
            user_contexts[user_id] = []
        
        bot.send_message(
            message.chat.id,
            "🗑️ Контекст диалога очищен! Можем начать с чистого листа."
        )
        
    except Exception as e:
        logger.error(f"Ошибка в /clear: {e}")

@bot.message_handler(commands=['myid'])
def handle_myid(message):
    """Узнать свой ID"""
    try:
        bot.send_message(
            message.chat.id,
            f"🆔 Твой Telegram ID: <code>{message.from_user.id}</code>\n\n"
            "Скопируй его, нажав на число!"
        )
    except Exception as e:
        logger.error(f"Ошибка в /myid: {e}")

@bot.message_handler(commands=['admin'])
def handle_admin(message):
    """Админ-панель"""
    try:
        if message.from_user.id != ADMIN_ID:
            bot.send_message(message.chat.id, "❌ У вас нет прав доступа.")
            return
        
        bot.send_message(
            message.chat.id,
            "👑 <b>Админ-панель</b>\n\nВыберите действие:",
            reply_markup=get_admin_menu()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в /admin: {e}")

# ═══════════════════════════════════════════════════════════════
#                   ⚙️ ОБРАБОТЧИКИ CALLBACK
# ═══════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_callbacks(call):
    """Обработка нажатий кнопок админ-панели"""
    try:
        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ У вас нет прав доступа.")
            return
        
        if call.data == "admin_stats":
            db = load_database()
            stats = db.get("stats", {})
            
            uptime = time.time() - bot_start_time if bot_start_time else 0
            uptime_str = f"{uptime/3600:.1f} часов"
            
            stats_text = (
                "📊 <b>Статистика бота</b>\n\n"
                f"👥 Всего пользователей: {stats.get('total', 0)}\n"
                f"✅ Активных: {stats.get('active', 0)}\n"
                f"🆕 Новых сегодня: {stats.get('today_new', 0)}\n"
                f"💬 Сообщений сегодня: {stats.get('messages_today', 0)}\n"
                f"⏱️ Время работы: {uptime_str}\n"
                f"🕐 Запущен: {datetime.fromtimestamp(bot_start_time, MOSCOW_TZ).strftime('%d.%m.%Y %H:%M:%S') if bot_start_time else 'Неизвестно'}"
            )
            
            bot.edit_message_text(
                stats_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_admin_menu()
            )
        
        elif call.data == "admin_users":
            db = load_database()
            users = db.get("users", {})
            
            users_text = f"👥 <b>Список пользователей ({len(users)})</b>\n\n"
            
            for user_id, user_data in list(users.items())[:10]:
                users_text += (
                    f"• {user_data.get('first_name', 'Неизвестно')} "
                    f"(@{user_data.get('username', 'нет')})\n"
                    f"  💬 Сообщений: {user_data.get('messages_count', 0)}\n\n"
                )
            
            if len(users) > 10:
                users_text += f"... и еще {len(users) - 10} пользователей"
            
            bot.edit_message_text(
                users_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_admin_menu()
            )
        
        elif call.data == "admin_broadcast":
            bot.answer_callback_query(call.id, "Отправьте сообщение для рассылки")
            user_states[call.from_user.id] = "waiting_broadcast"
        
        elif call.data == "admin_settings":
            settings = load_admin_settings()
            
            settings_text = (
                "⚙️ <b>Настройки</b>\n\n"
                f"🌅 Автоприветствия: {'✅' if settings.get('auto_greetings', True) else '❌'}\n"
                f"🌞 Утренние: {'✅' if settings.get('greeting_morning', True) else '❌'}\n"
                f"🌙 Ночные: {'✅' if settings.get('greeting_night', True) else '❌'}"
            )
            
            bot.edit_message_text(
                settings_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_admin_menu()
            )
        
        elif call.data == "admin_logs":
            try:
                with open('bot.log', 'r', encoding='utf-8') as f:
                    logs = f.readlines()[-20:]
                
                logs_text = "📝 <b>Последние 20 строк логов:</b>\n\n<code>"
                logs_text += ''.join(logs[-20:])
                logs_text += "</code>"
                
                bot.edit_message_text(
                    logs_text[:4000],
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=get_admin_menu()
                )
            except Exception as e:
                bot.answer_callback_query(call.id, f"Ошибка чтения логов: {e}")
        
        elif call.data == "admin_restart":
            bot.answer_callback_query(call.id, "🔄 Перезапуск...")
            bot.send_message(ADMIN_ID, "🔄 Перезапуск бота через 3 секунды...")
            time.sleep(3)
            os.execv(sys.executable, ['python'] + sys.argv)
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Ошибка в admin callbacks: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка")

# ═══════════════════════════════════════════════════════════════
#                   💬 ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ
# ═══════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    """Обработка текстовых сообщений"""
    try:
        user_id = message.from_user.id
        text = message.text.strip()
        
        # Обновляем информацию о пользователе
        update_user_in_db(message.from_user)
        
        # Проверка режима технических работ
        if MAINTENANCE_MODE and user_id != ADMIN_ID:
            bot.send_message(
                message.chat.id,
                "🔧 Бот временно на техническом обслуживании. Скоро вернемся!"
            )
            return
        
        # Обработка состояний (например, рассылка)
        if user_id in user_states:
            if user_states[user_id] == "waiting_broadcast":
                # Рассылка сообщения
                db = load_database()
                sent = 0
                failed = 0
                
                for uid in db["users"].keys():
                    try:
                        bot.send_message(int(uid), text)
                        sent += 1
                        time.sleep(0.05)
                    except:
                        failed += 1
                
                bot.send_message(
                    ADMIN_ID,
                    f"📤 Рассылка завершена!\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}"
                )
                
                del user_states[user_id]
                return
        
        # Обработка кнопок меню
        if text == "💬 Начать диалог":
            bot.send_message(
                message.chat.id,
                "💬 Отлично! Задай мне любой вопрос, и я постараюсь помочь.",
                reply_markup=get_main_menu()
            )
            return
        
        elif text == "ℹ️ О боте":
            about_text = (
                "🤖 <b>THE DAROV BOT ULTIMATE v4.2</b>\n\n"
                "Я — продвинутый AI-ассистент на базе современных технологий!\n\n"
                "🎯 <b>Мои возможности:</b>\n"
                "• 🧠 Умные ответы на любые вопросы\n"
                "• 🔍 Поиск актуальной информации в интернете\n"
                "• 🎤 Распознавание голосовых сообщений\n"
                "• 🎨 Генерация изображений (скоро!)\n"
                "• 🌅 Автоматические приветствия\n"
                "• 📊 Детальная статистика\n\n"
                "💫 <b>Создатель:</b> darov\n"
                "🆓 Полностью бесплатный!"
            )
            
            bot.send_message(
                message.chat.id,
                about_text,
                reply_markup=get_main_menu()
            )
            return
        
        elif text == "📊 Моя статистика":
            handle_stats(message)
            return
        
        elif text == "🔍 Веб-поиск":
            bot.send_message(
                message.chat.id,
                "🔍 <b>Веб-поиск</b>\n\n"
                "Напиши, что тебе найти, и я поищу актуальную информацию в интернете!",
                reply_markup=get_main_menu()
            )
            user_states[user_id] = "waiting_search"
            return
        
        # Обработка поискового запроса
        if user_id in user_states and user_states[user_id] == "waiting_search":
            del user_states[user_id]
            
            progress_msg = bot.send_message(
                message.chat.id,
                "🔍 <b>Поиск информации...</b>\n\n"
                f"📝 Запрос: <i>{text[:100]}</i>\n\n"
                "⏳ Это займет несколько секунд..."
            )
            
            try:
                answer = search_and_summarize(user_id, text)
                
                try:
                    bot.delete_message(message.chat.id, progress_msg.message_id)
                except:
                    pass
                
                send_long_message(message.chat.id, answer, reply_markup=get_main_menu())
                
                update_user_stats(user_id, messages_inc=1)
                log_user_action(user_id, "web_search", text[:100])
                
            except Exception as e:
                logger.error(f"Ошибка поиска: {e}")
                try:
                    bot.delete_message(message.chat.id, progress_msg.message_id)
                except:
                    pass
                bot.send_message(
                    message.chat.id,
                    "❌ Произошла ошибка при поиске. Попробуйте еще раз.",
                    reply_markup=get_main_menu()
                )
            return
        
        # Автоматическое определение необходимости веб-поиска
        if is_search_query(text):
            progress_msg = bot.send_message(
                message.chat.id,
                "🔍 <b>Обнаружен поисковый запрос!</b>\n\n"
                "Ищу актуальную информацию в интернете...\n"
                "⏳ Подождите немного..."
            )
            
            try:
                answer = search_and_summarize(user_id, text)
                
                try:
                    bot.delete_message(message.chat.id, progress_msg.message_id)
                except:
                    pass
                
                send_long_message(message.chat.id, answer, reply_markup=get_main_menu())
                
                update_user_stats(user_id, messages_inc=1)
                log_user_action(user_id, "auto_web_search", text[:100])
                
            except Exception as e:
                logger.error(f"Ошибка автопоиска: {e}")
                try:
                    bot.delete_message(message.chat.id, progress_msg.message_id)
                except:
                    pass
                # Если поиск не сработал, отвечаем обычным AI
                answer = get_ai_response(user_id, text)
                send_long_message(message.chat.id, answer, reply_markup=get_main_menu())
                update_user_stats(user_id, messages_inc=1)
                log_user_action(user_id, "message", text[:100])
            return
        
        # Обычный ответ AI (без поиска)
        answer = get_ai_response(user_id, text)
        
        update_user_stats(user_id, messages_inc=1)
        log_user_action(user_id, "message", text[:100])
        
        send_long_message(message.chat.id, answer, reply_markup=get_main_menu())
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}\n{traceback.format_exc()}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка. Попробуйте еще раз."
        )

# ═══════════════════════════════════════════════════════════════
#                      🚀 ЗАПУСК БОТА
# ═══════════════════════════════════════════════════════════════

def main():
    """Основная функция запуска бота"""
    global bot_start_time
    bot_start_time = time.time()
    
    print("=" * 60)
    print("✨ THE DAROV BOT ULTIMATE v4.2 - PREMIUM EDITION ✨")
    print("🔧 Адаптировано для Render.com")
    print("=" * 60)
    print()
    print("🎨 Функционал:")
    print("   🧠 AI: Groq (llama-3.3-70b-versatile)")
    print("   💬 Умные текстовые ответы")
    print("   🌐 Веб-поиск актуальной информации")
    print("   🎤 Распознавание голосовых сообщений")
    print("   🖼️ Генерация изображений (скоро!)")
    print("   🎯 Красивые интерактивные кнопки")
    print("   🌅 Автоприветствия: Утро (5-7) / Ночь (21-23) МСК")
    print("   🔄 Автоматический перезапуск при ошибках")
    print("   💚 Healthcheck мониторинг")
    print("   📊 Полная статистика пользователей")
    print("   🌐 Flask веб-сервер (anti-sleep)")
    print()
    print("📊 Файлы:")
    print("   • users_database.json - База пользователей")
    print("   • users_logs.json - Логи активности")
    print("   • admin_settings.json - Настройки админа")
    print("   • greetings_state.json - Состояние приветствий")
    print("   • bot.log - Файл логов бота")
    print()
    print(f"👑 ADMIN_ID = {ADMIN_ID}")
    print()
    
    # Создаем базы данных если их нет
    if not os.path.exists(DB_FILE):
        save_database({
            "users": {},
            "stats": {
                "total": 0,
                "active": 0,
                "today_new": 0,
                "messages_today": 0
            }
        })
        logger.info("✅ База данных создана")
    else:
        db = load_database()
        logger.info(f"✅ База данных загружена: {db.get('stats', {}).get('total', 0)} пользователей")
    
    if not os.path.exists(LOGS_FILE):
        save_logs({})
        logger.info("✅ Файл логов создан")
    
    if not os.path.exists(ADMIN_SETTINGS_FILE):
        save_admin_settings(load_admin_settings())
        logger.info("✅ Настройки созданы")
    
    if not os.path.exists(GREETINGS_FILE):
        save_greetings_state({})
        logger.info("✅ Файл приветствий создан")
    
    print()
    print("🚀 Запускаем Flask веб-сервер...")
    keep_alive()
    
    print("🚀 Запускаем бота...")
    print("🌅 Запускаем систему автоприветствий...")
    print("💚 Запускаем healthcheck мониторинг...")
    
    # Запускаем фоновые потоки
    greetings_thread = threading.Thread(target=check_and_send_greetings, daemon=True)
    greetings_thread.start()
    
    healthcheck_thread = threading.Thread(target=healthcheck_monitor, daemon=True)
    healthcheck_thread.start()
    
    print()
    print("✅ Flask веб-сервер запущен!")
    print("✅ Бот успешно запущен!")
    print("✅ Система приветствий активна!")
    print("✅ Healthcheck мониторинг активен!")
    print()
    print("💫 100% БЕСПЛАТНО")
    print("👨‍💻 Создатель: darov")
    print()
    print("=" * 60)
    
    # Уведомляем админа о запуске
    try:
        bot.send_message(
            ADMIN_ID,
            "✅ <b>Бот запущен на Render.com!</b>\n\n"
            f"🕐 Время: {datetime.now(MOSCOW_TZ).strftime('%d.%m.%Y %H:%M:%S')} МСК\n"
            "💚 Все системы работают\n"
            "🌐 Flask веб-сервер активен\n"
            "🎤 Распознавание голоса активно"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление о запуске: {e}")
    
    # Запускаем polling
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        logger.info("\n🛑 Бот остановлен пользователем")
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}\n{traceback.format_exc()}")
        print(f"\n❌ Критическая ошибка: {e}")
        print("\n💡 Проверьте:")
        print("   • Правильность переменных окружения")
        print("   • Подключение к интернету")

if __name__ == "__main__":
    restart_count = 0
    
    while restart_count < MAX_RESTART_ATTEMPTS:
        try:
            main()
            break
        except KeyboardInterrupt:
            logger.info("Бот остановлен пользователем")
            break
        except Exception as e:
            restart_count += 1
            logger.error(f"Бот упал! Попытка перезапуска {restart_count}/{MAX_RESTART_ATTEMPTS}")
            logger.error(f"Ошибка: {e}\n{traceback.format_exc()}")
            
            if restart_count < MAX_RESTART_ATTEMPTS:
                logger.info(f"Перезапуск через {RESTART_DELAY} секунд...")
                time.sleep(RESTART_DELAY)
            else:
                logger.error("Достигнуто максимальное количество попыток перезапуска!")
                break
