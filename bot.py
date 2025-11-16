import os
import csv
import re
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram import F
from dotenv import load_dotenv
from aiohttp import web
import asyncio

# === Загрузка переменных окружения ===
load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("❌ TOKEN не найден! Убедитесь, что он записан в .env")

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# === Health-check ===
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
with open("songs.csv", "r", encoding="utf-8") as f:
    hymns = list(csv.DictReader(f, delimiter=';'))

current_collection = None

# === Команды ===
@dp.message(F.text == "/start")
async def start(message: types.Message):
    await message.answer("Выберите сборник гимнов:", reply_markup=main_keyboard)

@dp.message(F.text.in_(["Красный сборник", "Молодёжный сборник"]))
async def choose_collection(message: types.Message):
    global current_collection
    current_collection = "red" if message.text == "Красный сборник" else "youth"
    await message.answer(
        f"📖 Активирован {message.text}. Введите номер или часть названия гимна.",
        reply_markup=main_keyboard
    )

# === Отправка страниц гимна ===
async def send_hymn_pages(message, hymn):
    folder = hymn["collection"]
    number = hymn["number"]

    pages = [
        f for f in os.listdir(folder)
        if re.match(fr"^{re.escape(number)}(_|\.)", f)
    ]

    if not pages:
        await message.answer("⚠️ Страницы не найдены.", reply_markup=main_keyboard)
        return

    for page in sorted(pages):
        with open(os.path.join(folder, page), "rb") as photo:
            await message.answer_photo(photo)

# === Поиск по номеру ===
@dp.message(lambda msg: msg.text and re.search(r'\d+', msg.text))
async def search_by_number(message: types.Message):
    global current_collection
    if not current_collection:
        await message.answer("Сначала выберите сборник.", reply_markup=main_keyboard)
        return

    number = re.search(r"(\d+)", message.text).group(1)

    hymn = next(
        (h for h in hymns if h["number"] == number and h["collection"] == current_collection),
        None
    )

    if hymn:
        await send_hymn_pages(message, hymn)
    else:
        await message.answer("Гимн с таким номером не найден.", reply_markup=main_keyboard)

# === Поиск по названию ===
@dp.message(lambda msg: msg.text and not re.search(r'\d+', msg.text))
async def search_by_title(message: types.Message):
    global current_collection
    if not current_collection:
        await message.answer("Сначала выберите сборник.", reply_markup=main_keyboard)
        return

    query = message.text.lower()

    matches = [
        h for h in hymns
        if query in h["title"].lower() and h["collection"] == current_collection
    ]

    if not matches:
        await message.answer("Гимн не найден 😢")
        return

    if len(matches) == 1:
        await send_hymn_pages(message, matches[0])
    else:
        text = "🔍 Найдено несколько гимнов:\n\n"
        text += "\n".join(f"{h['number']} — {h['title']}" for h in matches)
        await message.answer(text)

# === Основной запуск ===
async def main():
    # Запуск health-check сервера
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 800)
    await site.start()
    print("🌐 Health-check сервер: порт 800")

    # Старт Telegram
    print("🤖 Telegram-бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
