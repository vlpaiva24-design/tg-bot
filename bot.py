import asyncio
import os

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from db import save_request


TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = -5221185330

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


TEXTS = {
    "ru": {
        "start": "Привет! Это компания SmokeZone 👋\n\nВы можете оставить:\nжалобу, предложение или другое обращение.\n\nВыберите тип обращения 👇",
        "name": "Укажите, пожалуйста, как вас зовут:",
        "phone": "Пожалуйста, поделитесь номером телефона 👇",
        "branch": "Выберите филиал 👇",
        "text": "Напишите текст обращения:",
        "custom_branch": "Напишите ориентир филиала:",
        "done": "✅ Обращение отправлено!\n\nМы постараемся ответить вам в ближайшее время.",
        "again": "Хотите оставить ещё одно обращение?"
    }
}


def get_text(user, key):
    return TEXTS["ru"][key]


class Form(StatesGroup):
    req_type = State()
    name = State()
    phone = State()
    branch = State()
    custom_branch = State()
    text = State()


# ✅ кнопки теперь В СТОЛБИК
def get_type_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Жалоба", callback_data="type_Жалоба")],
        [InlineKeyboardButton("Предложение", callback_data="type_Предложение")],
        [InlineKeyboardButton("Другое", callback_data="type_Другое")]
    ])


def get_branch_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Корзинка Сайрам", callback_data="branch_Корзинка Сайрам")],
        [InlineKeyboardButton("Транспортный (Хавас)", callback_data="branch_Транспортный (Хавас)")],
        [InlineKeyboardButton("Написать ориентир", callback_data="branch_custom")]
    ])


# ✅ кнопка "ещё раз"
def restart_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Оставить ещё обращение", callback_data="restart")]
    ])


contact_kb = ReplyKeyboardMarkup(
    resize_keyboard=True,
    one_time_keyboard=True
).add(
    KeyboardButton("Поделиться номером", request_contact=True)
)


@dp.message_handler(commands=["start"])
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(get_text(message.from_user, "start"), reply_markup=get_type_kb())
    await Form.req_type.set()


@dp.callback_query_handler(lambda c: c.data.startswith("type_"), state="*")
async def process_type(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(req_type=callback.data.split("_", 1)[1])
    await callback.message.answer(get_text(callback.from_user, "name"))
    await Form.name.set()
    await callback.answer()


@dp.message_handler(state=Form.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(get_text(message.from_user, "phone"), reply_markup=contact_kb)
    await Form.phone.set()


# ✅ скрываем кнопку после отправки номера
@dp.message_handler(state=Form.phone, content_types=types.ContentType.CONTACT)
async def get_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)

    await message.answer(
        get_text(message.from_user, "branch"),
        reply_markup=get_branch_kb()
    )

    # 🔥 вот это скрывает кнопку
    await message.answer(" ", reply_markup=ReplyKeyboardRemove())

    await Form.branch.set()


@dp.callback_query_handler(lambda c: c.data.startswith("branch_"), state="*")
async def process_branch(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "branch_custom":
        await callback.message.answer(get_text(callback.from_user, "custom_branch"))
        await Form.custom_branch.set()
    else:
        await state.update_data(branch=callback.data.split("_", 1)[1])
        await callback.message.answer(get_text(callback.from_user, "text"))
        await Form.text.set()

    await callback.answer()


@dp.message_handler(state=Form.custom_branch)
async def custom_branch(message: types.Message, state: FSMContext):
    await state.update_data(branch=message.text)
    await message.answer(get_text(message.from_user, "text"))
    await Form.text.set()


# ✅ нормальный формат сообщения в группу
@dp.message_handler(state=Form.text)
async def finish(message: types.Message, state: FSMContext):
    data = await state.get_data()

    save_request(
        user_id=message.from_user.id,
        name=data["name"],
        phone=data["phone"],
        req_type=data["req_type"],
        branch=data["branch"],
        text=message.text
    )

    text_msg = f"""
📩 Новое обращение

📌 Тип: {data['req_type']}
👤 Имя: {data['name']}
📞 Телефон: {data['phone']}
🏢 Филиал: {data['branch']}

📝 Текст:
{message.text}
"""

    await bot.send_message(ADMIN_CHAT_ID, text_msg)

    await message.answer(get_text(message.from_user, "done"))
    await message.answer(get_text(message.from_user, "again"), reply_markup=restart_kb())

    await state.finish()


# ✅ рестарт
@dp.callback_query_handler(lambda c: c.data == "restart", state="*")
async def restart(callback: types.CallbackQuery, state: FSMContext):
    await start(callback.message, state)
    await callback.answer()


if __name__ == "__main__":
    print("Бот запущен...")
    from aiogram import executor
    executor.start_polling(dp)
