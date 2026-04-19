import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from db import save_request

import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = -5221185330  # ВСТАВЬ СВОЙ ID

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# 🔹 Тексты
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
    lang = user.language_code
    if lang not in TEXTS:
        lang = "ru"
    return TEXTS[lang][key]


# 🔹 Состояния
class Form(StatesGroup):
    req_type = State()
    name = State()
    phone = State()
    branch = State()
    custom_branch = State()
    text = State()


# 🔹 Inline кнопки
def get_type_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Жалоба", callback_data="type_Жалоба")],
        [InlineKeyboardButton(text="Предложение", callback_data="type_Предложение")],
        [InlineKeyboardButton(text="Другое", callback_data="type_Другое")]
    ])


def get_branch_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Корзинка Сайрам", callback_data="branch_Корзинка Сайрам")],
        [InlineKeyboardButton(text="Корзинка Салом", callback_data="branch_Корзинка Салом")],
        [InlineKeyboardButton(text="Корзинка Малика", callback_data="branch_Корзинка Малика")],
        [InlineKeyboardButton(text="Корзинка Петушок", callback_data="branch_Корзинка Петушок")],
        [InlineKeyboardButton(text="Транспортный (Хавас)", callback_data="branch_Транспортный (Хавас)")],
        [InlineKeyboardButton(text="Ташкент Маркет (Кристал)", callback_data="branch_Ташкент Маркет (Кристал)")],
        [InlineKeyboardButton(text="Написать ориентир", callback_data="branch_custom")]
    ])


def restart_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оставить ещё обращение", callback_data="restart")]
    ])


# 🔹 контакт
contact_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Поделиться номером", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)


# 🔹 старт
async def start_flow(message: types.Message, state: FSMContext):
    await state.clear()

    await message.answer(
        get_text(message.from_user, "start"),
        reply_markup=get_type_kb()
    )

    await state.set_state(Form.req_type)


@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await start_flow(message, state)


# 🔹 тип обращения
@dp.callback_query(lambda c: c.data.startswith("type_"))
async def process_type(callback: types.CallbackQuery, state: FSMContext):
    req_type = callback.data.split("_", 1)[1]

    await state.update_data(req_type=req_type)

    await callback.message.edit_reply_markup()
    await callback.message.answer(get_text(callback.from_user, "name"))

    await state.set_state(Form.name)
    await callback.answer()


# 🔹 имя
@dp.message(Form.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)

    await message.answer(
        get_text(message.from_user, "phone"),
        reply_markup=contact_kb
    )

    await state.set_state(Form.phone)


# 🔹 телефон
@dp.message(Form.phone)
async def get_phone(message: types.Message, state: FSMContext):
    if not message.contact:
        await message.answer(get_text(message.from_user, "phone"))
        return

    await state.update_data(phone=message.contact.phone_number)

    await message.answer(
        get_text(message.from_user, "branch"),
        reply_markup=get_branch_kb()
    )

    await state.set_state(Form.branch)


# 🔹 филиал
@dp.callback_query(lambda c: c.data.startswith("branch_"))
async def process_branch(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data

    await callback.message.edit_reply_markup()

    if data == "branch_custom":
        await callback.message.answer(get_text(callback.from_user, "custom_branch"))
        await state.set_state(Form.custom_branch)
    else:
        branch = data.split("_", 1)[1]  # ВАЖНО: сохраняет весь текст
        await state.update_data(branch=branch)

        await callback.message.answer(get_text(callback.from_user, "text"))
        await state.set_state(Form.text)

    await callback.answer()


# 🔹 кастом филиал
@dp.message(Form.custom_branch)
async def custom_branch(message: types.Message, state: FSMContext):
    await state.update_data(branch=message.text)

    await message.answer(get_text(message.from_user, "text"))
    await state.set_state(Form.text)


# 🔹 финал
@dp.message(Form.text)
async def get_text_handler(message: types.Message, state: FSMContext):
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

    await state.clear()


# 🔹 рестарт
@dp.callback_query(lambda c: c.data == "restart")
async def restart(callback: types.CallbackQuery, state: FSMContext):
    await start_flow(callback.message, state)
    await callback.answer()


# 🔹 запуск
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

