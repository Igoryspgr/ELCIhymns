import os
import csv
import re
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from PIL import Image
from dotenv import load_dotenv
from aiohttp import web   # <----- добавлено

# === Загрузка переменных окружения ===
load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("❌ TOKEN не найден! Убедитесь, что он записан в .env")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# === Запускаем веб-сервер для Koyeb Health Check ===
async def health(request):
    return web.Response(text="OK", status=200)

app = web.Application()
app.router.add_get("/health", health)

# === Главное меню ===
main_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_keyboard.add("Красный сборник", "Молодёжный сборник")

# === Настройка логирования ===
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/errors.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def log_usage(user_id, collection, hymn_number):
    os.makedirs("logs", exist_ok=True)
    with open("logs/usage_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | user_id={user_id} | collection={collection} | hymn_number={hymn_number}\n")

def log_action(user_id, action):
    os.makedirs("logs", exist_ok=True)
    with open("logs/log.csv", "a", encoding="utf-8") as log:
        log.write(f"{user_id};{action}\n")

# === Загрузка гимнов ===
hymns = []
with open('songs.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        hymns.append(row)

current_collection = None

# === Команды ===
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Выберите сборник гимнов:", reply_markup=main_keyboard)
    log_action(message.from_user.id, "start")

@dp.message_handler(lambda message: message.text in ["Красный сборник", "Молодёжный сборник"])
async def choose_collection(message: types.Message):
    global current_collection
    current_collection = "red" if message.text == "Красный сборник" else "youth"
    await message.answer(f"📖 Активирован {message.text}. Введите номер или часть названия гимна.", reply_markup=main_keyboard)
    log_action(message.from_user.id, f"choose_collection:{current_collection}")

# === Отправка страниц гимна ===
async def send_hymn_pages(message, hymn):
    try:
        folder = hymn['collection']
        number = hymn['number']
        pages = [
            f for f in os.listdir(folder)
            if re.match(fr'^{re.escape(number)}(_|\.)', f)
        ]
        if not pages:
            await message.answer("⚠️ Страницы для этого гимна не найдены.", reply_markup=main_keyboard)
            return
        for page in sorted(pages):
            with open(os.path.join(folder, page), 'rb') as photo:
                await message.answer_photo(photo, reply_markup=main_keyboard)
        log_action(message.from_user.id, f"send_hymn:{folder}:{number}")
        log_usage(message.from_user.id, folder, number)
    except Exception:
        logging.exception(f"Ошибка при отправке гимна {hymn['number']} ({hymn['collection']})")

# === Поиск по номеру ===
@dp.message_handler(lambda message: re.search(r'\d+', message.text.strip()))
async def search_by_number_only_digits(message: types.Message):
    global current_collection
    if not current_collection:
        await message.answer("Сначала выберите сборник.", reply_markup=main_keyboard)
        return

    try:
        number_match = re.search(r'(\d+)', message.text.strip())
        if not number_match:
            await message.answer("Не удалось определить номер гимна.", reply_markup=main_keyboard)
            return

        number = number_match.group(1).strip()

        match = next(
            (h for h in hymns
             if h['number'].strip() == number and h['collection'] == current_collection),
            None
        )

        if match:
            await send_hymn_pages(message, match)
        else:
            await message.answer("Гимн с таким номером не найден.", reply_markup=main_keyboard)

        log_action(message.from_user.id, f"search_number:{number}")
    except Exception:
        logging.exception(f"Ошибка при поиске по номеру ({message.text})")

# === Поиск по названию ===
def search_hymn_by_title(title_query, hymns, collection):
    return [
        hymn for hymn in hymns
        if title_query.lower() in hymn['title'].lower() and hymn['collection'] == collection
    ]

@dp.message_handler(lambda message: message.text and not re.search(r'\d+', message.text.strip()))
async def handle_text_search(message: types.Message):
    global current_collection
    if not current_collection:
        await message.answer("Сначала выберите сборник.", reply_markup=main_keyboard)
        return

    query = message.text.strip()
    try:
        matches = search_hymn_by_title(query, hymns, current_collection)

        if not matches:
            await message.answer("Гимн не найден 😢", reply_markup=main_keyboard)
            return

        if len(matches) == 1:
            await send_hymn_pages(message, matches[0])
        else:
            text = "🔍 Найдено несколько гимнов. Выберите номер:\n\n"
            for hymn in matches:
                text += f"{hymn['number']} — {hymn['title']}\n"
            await message.answer(text, reply_markup=main_keyboard)

        log_action(message.from_user.id, f"search_title:{query}")
    except Exception:
        logging.exception(f"Ошибка при поиске по названию ({query})")

# === Запуск ===
if __name__ == '__main__':
    print("🤖 Бот запущен!")

    # Запускаем веб-сервер health-check
    import threading
    threading.Thread(target=lambda: web.run_app(app, host="0.0.0.0", port=8000)).start()

    # Запускаем Telegram-бота
    executor.start_polling(dp, skip_updates=True)
