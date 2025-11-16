import os
import csv
import re
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from PIL import Image
from dotenv import load_dotenv
from aiohttp import web
import asyncio

# === Загрузка переменных окружения ===
load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("❌ TOKEN не найден!")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# === Health-check endpoint ===
async def health(request):
    return web.Response(text="OK", status=200)

app = web.Application()
app.router.add_get("/health", health)

# === Главное меню ===
main_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_keyboard.add("Красный сборник", "Молодёжный сборник")

# === Логирование ===
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/errors.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# === Загрузка гимнов ===
hymns = []
with open('songs.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    hymns = list(reader)

current_collection = None

# === Команды ===
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Выберите сборник гимнов:", reply_markup=main_keyboard)

@dp.message_handler(lambda m: m.text in ["Красный сборник", "Молодёжный сборник"])
async def choose_collection(message: types.Message):
    global current_collection
    current_collection = "red" if message.text == "Красный сборник" else "youth"

    await message.answer(
        f"📖 Активирован {message.text}. Введите номер или часть названия гимна.",
        reply_markup=main_keyboard
    )

# === Отправка страниц ===
async def send_hymn_pages(message, hymn):
    folder = hymn['collection']
    number = hymn['number']

    pages = [
        f for f in os.listdir(folder)
        if re.match(fr'^{re.escape(number)}(_|\.)', f)
    ]

    if not pages:
        await message.answer("⚠️ Страницы не найдены.")
        return

    for page in sorted(pages):
        with open(os.path.join(folder, page), "rb") as photo:
            await message.answer_photo(photo)

# === Основной запуск ===
async def main():
    # запускаем health-check сервер
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host="0.0.0.0", port=800)
    await site.start()
    print("🌐 Health-check сервер запущен на порту 800")

    # запускаем Telegram-бота
    print("🤖 Telegram-бот запущен!")
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
