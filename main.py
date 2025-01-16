import sqlite3
import json
import asyncio
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import logging

with open("config.json", "r") as config_file:
    config = json.load(config_file)

API_TOKEN = config["API_TOKEN"]
administrators = config["ADMIN_IDS"]

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

conn = sqlite3.connect("queue_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    in_queue BOOLEAN
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    notified BOOLEAN DEFAULT FALSE,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
)
""")

try:
    cursor.execute("SELECT notified FROM queue LIMIT 1")
except sqlite3.OperationalError:
    cursor.execute("ALTER TABLE queue ADD COLUMN notified BOOLEAN DEFAULT FALSE")
    conn.commit()

try:
    cursor.execute("SELECT username FROM queue LIMIT 1")
except sqlite3.OperationalError:
    cursor.execute("ALTER TABLE queue ADD COLUMN username TEXT")
    conn.commit()

def export_to_excel():
    users_df = pd.read_sql_query("SELECT * FROM users", conn)
    queue_df = pd.read_sql_query("SELECT * FROM queue", conn)

    with pd.ExcelWriter("queue_data.xlsx") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        queue_df.to_excel(writer, sheet_name="Queue", index=False)

    return "queue_data.xlsx"

def is_admin(user_id):
    return user_id in administrators

def get_user_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton("➕ Добавиться", callback_data="add_to_queue"),
        InlineKeyboardButton("➖ Удалиться", callback_data="remove_from_queue"),
        InlineKeyboardButton("🔍 место", callback_data="position_in_queue"),
        InlineKeyboardButton("👀 очередь", callback_data="list_queue")
    )
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton("➕ Добавиться", callback_data="add_to_queue"),
        InlineKeyboardButton("➖ Удалиться", callback_data="remove_from_queue"),
        InlineKeyboardButton("🔍 место", callback_data="position_in_queue"),
        InlineKeyboardButton("👀 очередь", callback_data="list_queue"),
        InlineKeyboardButton("🧹 Очистить", callback_data="clear_queue"),
        InlineKeyboardButton("📤 Экспорт", callback_data="export_to_excel")
    )
    return keyboard

@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, username, in_queue)
    VALUES (?, ?, ?)
    """, (user_id, username, False))
    conn.commit()

    if is_admin(user_id):
        await message.reply("Привет, солнышко! Используй кнопочки для работы с ботом.", reply_markup=get_admin_keyboard())
    else:
        await message.reply("Вот вам ботяра, чтобы в чат не спамили!", reply_markup=get_user_keyboard())

@dp.message_handler(commands=["export"])
async def export_data(message: types.Message):
    user_id = message.from_user.id

    if is_admin(user_id):
        file_name = export_to_excel()
        with open(file_name, "rb") as file:
            await message.reply_document(file, caption="Данные экспортированы в Excel.")
    else:
        await message.reply("Эта команда доступна только администраторам.")

@dp.callback_query_handler(lambda query: query.data == "add_to_queue")
async def add_to_queue(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or callback_query.from_user.first_name

    cursor.execute("SELECT in_queue FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if user and user[0]:
        await callback_query.answer("Вы уже в очереди!")
    else:
        cursor.execute("INSERT INTO queue (user_id, username) VALUES (?, ?)", (user_id, username))
        cursor.execute("UPDATE users SET in_queue = ? WHERE user_id = ?", (True, user_id))
        conn.commit()

        cursor.execute("SELECT COUNT(*) FROM queue WHERE id <= (SELECT id FROM queue WHERE user_id = ?)", (user_id,))
        position = cursor.fetchone()[0]

        await callback_query.answer(f"Вы добавлены в очередь. Ваш номер: {position}.")

@dp.callback_query_handler(lambda query: query.data == "remove_from_queue")
async def remove_from_queue(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if is_admin(user_id):
        cursor.execute("DELETE FROM queue WHERE user_id = ?", (user_id,))
        cursor.execute("UPDATE users SET in_queue = ? WHERE user_id = ?", (False, user_id))
        conn.commit()
        await callback_query.answer("Вы удалены из очереди администратором.")
    else:
        cursor.execute("SELECT in_queue FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if user and user[0]:
            cursor.execute("DELETE FROM queue WHERE user_id = ?", (user_id,))
            cursor.execute("UPDATE users SET in_queue = ? WHERE user_id = ?", (False, user_id))
            conn.commit()
            await callback_query.answer("Вы удалены из очереди.")
        else:
            await callback_query.answer("Вас нет в очереди.")

@dp.callback_query_handler(lambda query: query.data == "position_in_queue")
async def position_in_queue(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    cursor.execute("SELECT COUNT(*) FROM queue WHERE id <= (SELECT id FROM queue WHERE user_id = ?)", (user_id,))
    position = cursor.fetchone()

    if position and position[0] > 0:
        await callback_query.answer(f"Ваше место в очереди: {position[0]}.")
    else:
        await callback_query.answer("Вас нет в очереди.")

@dp.callback_query_handler(lambda query: query.data == "list_queue")
async def list_queue(callback_query: types.CallbackQuery):
    cursor.execute("SELECT users.username FROM queue JOIN users ON queue.user_id = users.user_id ORDER BY queue.id")
    queue_list = cursor.fetchall()

    if queue_list:
        response = "Очередь:\n" + "\n".join([f"{i + 1}. {user[0]}" for i, user in enumerate(queue_list)])
        await callback_query.message.answer(response)
    else:
        await callback_query.message.answer("Очередь пуста.")

@dp.callback_query_handler(lambda query: query.data == "clear_queue")
async def clear_queue(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if is_admin(user_id):
        cursor.execute("DELETE FROM queue")
        cursor.execute("UPDATE users SET in_queue = ?", (False,))
        conn.commit()
        await callback_query.message.answer("Очередь очищена.")
    else:
        await callback_query.answer("Эта команда доступна только администраторам.")

@dp.callback_query_handler(lambda query: query.data == "export_to_excel")
async def export_to_excel_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if is_admin(user_id):
        file_name = export_to_excel()
        with open(file_name, "rb") as file:
            await callback_query.message.reply_document(file, caption="Данные экспортированы в Excel.")
    else:
        await callback_query.answer("Эта команда доступна только администраторам.")

async def notify_next():
    while True:
        cursor.execute("SELECT user_id, username FROM queue WHERE notified = FALSE ORDER BY id LIMIT 1")
        next_user = cursor.fetchone()

        if next_user:
            user_id, username = next_user
            await bot.send_message(user_id, f"Ты следующий, {username}!")

            cursor.execute("UPDATE queue SET notified = TRUE WHERE user_id = ?", (user_id,))
            conn.commit()

        await asyncio.sleep(10)

@dp.message_handler()
async def unknown_command(message: types.Message):
    await message.reply("Неизвестная команда. Используй кнопки для работы с ботом.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def main():
        asyncio.create_task(notify_next())
        await dp.start_polling(bot)

    asyncio.run(main())