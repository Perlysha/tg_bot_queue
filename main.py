import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton
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

user_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
user_keyboard.add(KeyboardButton("Добавиться в очередь"))
user_keyboard.add(KeyboardButton("Удалиться из очереди"))
user_keyboard.add(KeyboardButton("Узнать своё место"))
user_keyboard.add(KeyboardButton("Просмотреть очередь"))

admin_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
admin_keyboard.add(KeyboardButton("Добавиться в очередь"))
admin_keyboard.add(KeyboardButton("Удалиться из очереди"))
admin_keyboard.add(KeyboardButton("Узнать своё место"))
admin_keyboard.add(KeyboardButton("Просмотреть очередь"))
admin_keyboard.add(KeyboardButton("Очистить очередь"))

@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    if user_id not in users_accounts:
        users_accounts[user_id] = {"username": username, "in_queue": False}

    if is_admin(user_id):
        await message.reply("Привет, администратор! Используй кнопки для работы с ботом.", reply_markup=admin_keyboard)
    else:
        await message.reply("Привет! Используй кнопки для работы с ботом.", reply_markup=user_keyboard)

@dp.message_handler(lambda message: message.text == "Добавиться в очередь")
async def add_to_queue(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    if user_id in queue:
        await message.reply("Вы уже в очереди!")
    else:
        queue.append(user_id)
        users_accounts[user_id]["in_queue"] = True
        await message.reply(f"Вы добавлены в очередь. Ваш номер: {len(queue)}.")

@dp.message_handler(lambda message: message.text == "Удалиться из очереди")
async def remove_from_queue(message: types.Message):
    user_id = message.from_user.id

    if user_id in queue:
        queue.remove(user_id)
        users_accounts[user_id]["in_queue"] = False
        await message.reply("Вы удалены из очереди.")
    else:
        await message.reply("Вас нет в очереди.")

@dp.message_handler(lambda message: message.text == "Узнать своё место")
async def position_in_queue(message: types.Message):
    user_id = message.from_user.id

    if user_id in queue:
        position = queue.index(user_id) + 1
        await message.reply(f"Ваше место в очереди: {position}.")
    else:
        await message.reply("Вас нет в очереди.")

@dp.message_handler(lambda message: message.text == "Просмотреть очередь")
async def list_queue(message: types.Message):
    user_id = message.from_user.id

    if queue:
        if is_admin(user_id):
            users_list = "\n".join([f"{i + 1}. {users_accounts[user_id]['username']} (ID: {user_id})" for i, user_id in enumerate(queue)])
            await message.reply(f"Очередь:\n{users_list}")
        else:
            users_list = "\n".join([f"{i + 1}. {users_accounts[user_id]['username']}" for i, user_id in enumerate(queue)])
            await message.reply(f"Очередь:\n{users_list}")
    else:
        await message.reply("Очередь пуста.")

@dp.message_handler(lambda message: message.text == "Очистить очередь")
async def clear_queue(message: types.Message):
    user_id = message.from_user.id

    if is_admin(user_id):
        queue.clear()
        for user in users_accounts:
            users_accounts[user]["in_queue"] = False
        await message.reply("Очередь очищена.")
    else:
        await message.reply("Эта команда доступна только администраторам.")

@dp.message_handler()
async def unknown_command(message: types.Message):
    await message.reply("Неизвестная команда. Используй кнопки для работы с ботом.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)