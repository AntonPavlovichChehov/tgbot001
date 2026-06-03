from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import json
import os

TOKEN = "8211178139:AAG1niMdrR8-Y91i_GBGYMREofC6zzOfet4"

ADMIN_IDS = [
    8028254082,
    8285874260,
    75558139187,
    7570116797
]

GROUPS_FILE = "groups.json"

BTN_BROADCAST = "📢 Отправить рассылку"

user_states = {}


def load_groups():
    if not os.path.exists(GROUPS_FILE):
        return set()

    with open(GROUPS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
        return set(data)


def save_groups(groups):
    with open(GROUPS_FILE, "w", encoding="utf-8") as file:
        json.dump(list(groups), file)


groups = load_groups()


def is_admin(user_id):
    return user_id in ADMIN_IDS


def main_keyboard():
    return ReplyKeyboardMarkup(
        [[BTN_BROADCAST]],
        resize_keyboard=True
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id

    if chat.type != "private":
        await update.message.reply_text("Бот работает ✅")
        return

    if not is_admin(user_id):
        await update.message.reply_text("У тебя нет доступа.")
        return

    await update.message.reply_text(
        "Выбери действие:",
        reply_markup=main_keyboard()
    )


async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Эту команду нужно писать в группе.")
        return

    groups.add(chat.id)
    save_groups(groups)

    await update.message.reply_text("Группа добавлена ✅")


async def groups_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(f"Сохранено групп: {len(groups)}")


async def send_broadcast(context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    success = 0
    failed = 0

    for group_id in groups:
        try:
            await context.bot.send_message(chat_id=group_id, text=text)
            success += 1
        except Exception:
            failed += 1

    await context.bot.send_message(
        chat_id=user_id,
        text=f"Рассылка отправлена ✅\nОтправлено: {success}\nОшибок: {failed}",
        reply_markup=main_keyboard()
    )


async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user_id = update.effective_user.id
    text = update.message.text

    if not is_admin(user_id):
        await update.message.reply_text("У тебя нет доступа.")
        return

    if text == BTN_BROADCAST:
        user_states[user_id] = "waiting_text"
        await update.message.reply_text("Вставь текст рассылки:")
        return

    if user_states.get(user_id) == "waiting_text":
        user_states.pop(user_id, None)
        await update.message.reply_text("Отправляю рассылку...")
        await send_broadcast(context, user_id, text)
        return

    await update.message.reply_text(
        "Выбери действие:",
        reply_markup=main_keyboard()
    )


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("У тебя нет доступа.")
        return

    text = " ".join(context.args)

    if not text:
        await update.message.reply_text("Напиши текст после команды /broadcast")
        return

    await update.message.reply_text("Отправляю рассылку...")
    await send_broadcast(context, update.effective_user.id, text)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addgroup", add_group))
    app.add_handler(CommandHandler("groups", groups_count))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_private_message))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()