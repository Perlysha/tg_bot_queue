import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters import Command
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import logging

with open("config.json", "r") as config_file:
    config = json.load(config_file)

API_TOKEN = config["API_TOKEN"]
administrators = config["ADMIN_IDS"]

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

queue = []
users_accounts = {}

def is_admin(user_id):
    return user_id in administrators

def get_user_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Добавиться в очередь", callback_data="add_to_queue"),
        InlineKeyboardButton("➖ Удалиться из очереди", callback_data="remove_from_queue"),
        InlineKeyboardButton("🔍 Узнать своё место", callback_data="position_in_queue"),
        InlineKeyboardButton("👀 Просмотреть очередь", callback_data="list_queue")
    )
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Добавиться в очередь", callback_data="add_to_queue"),
        InlineKeyboardButton("➖ Удалиться из очереди", callback_data="remove_from_queue"),
        InlineKeyboardButton("🔍 Узнать своё место", callback_data="position_in_queue"),
        InlineKeyboardButton("👀 Просмотреть очередь", callback_data="list_queue"),
        InlineKeyboardButton("🧹 Очистить очередь", callback_data="clear_queue")
    )
    return keyboard

@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    if user_id not in users_accounts:
        users_accounts[user_id] = {"username": username, "in_queue": False}

    if is_admin(user_id):
        await message.reply("Привет, солнышко! Используй кнопочки для работы с ботом.", reply_markup=get_admin_keyboard())
    else:
        await message.reply("Вот вам ботяра, чтобы в чат не спамили!", reply_markup=get_user_keyboard())

@dp.callback_query_handler(lambda query: query.data == "add_to_queue")
async def add_to_queue(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username or callback_query.from_user.first_name

    if user_id not in users_accounts:
        users_accounts[user_id] = {"username": username, "in_queue": False}

    if user_id in queue:
        await callback_query.answer("Вы уже в очереди!")
    else:
        queue.append(user_id)
        users_accounts[user_id]["in_queue"] = True
        await callback_query.answer(f"Вы добавлены в очередь. Ваш номер: {len(queue)}.")

@dp.callback_query_handler(lambda query: query.data == "remove_from_queue")
async def remove_from_queue(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id in queue:
        queue.remove(user_id)
        users_accounts[user_id]["in_queue"] = False
        await callback_query.answer("Вы удалены из очереди.")
    else:
        await callback_query.answer("Вас нет в очереди.")

@dp.callback_query_handler(lambda query: query.data == "position_in_queue")
async def position_in_queue(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id in queue:
        position = queue.index(user_id) + 1
        await callback_query.answer(f"Ваше место в очереди: {position}.")
    else:
        await callback_query.answer("Вас нет в очереди.")

@dp.callback_query_handler(lambda query: query.data == "list_queue")
async def list_queue(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if queue:
        if is_admin(user_id):
            users_list = []
            for i, user_id_in_queue in enumerate(queue):
                if user_id_in_queue in users_accounts:
                    username = users_accounts[user_id_in_queue]["username"]
                    users_list.append(f"{i + 1}. {username} (ID: {user_id_in_queue})")
                else:
                    users_list.append(f"{i + 1}. Неизвестный пользователь (ID: {user_id_in_queue})")
            await callback_query.message.answer(f"Очередь:\n" + "\n".join(users_list))
        else:
            users_list = []
            for i, user_id_in_queue in enumerate(queue):
                if user_id_in_queue in users_accounts:
                    username = users_accounts[user_id_in_queue]["username"]
                    users_list.append(f"{i + 1}. {username}")
                else:
                    users_list.append(f"{i + 1}. Неизвестный пользователь")
            await callback_query.message.answer(f"Очередь:\n" + "\n".join(users_list))
    else:
        await callback_query.message.answer("Очередь пуста.")

@dp.callback_query_handler(lambda query: query.data == "clear_queue")
async def clear_queue(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if is_admin(user_id):
        queue.clear()
        for user in users_accounts:
            users_accounts[user]["in_queue"] = False
        await callback_query.message.answer("Очередь очищена.")
    else:
        await callback_query.answer("Эта команда доступна только администраторам.")

@dp.message_handler()
async def unknown_command(message: types.Message):
    await message.reply("Неизвестная команда. Используй кнопки для работы с ботом.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)