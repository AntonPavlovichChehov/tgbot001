from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ChatMemberHandler
import json
import os

import os

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [
    8028254082,
    8285874260,
    8337162707,
    8692231675,
    7558139187,
    7570116797
]

GROUPS_FILE = "/data/groups.json"

BTN_BROADCAST = "📢 Отправить рассылку"
BROADCAST_FOOTER = """

Курс?
%?

"""
user_states = {}
pending_messages = {}


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


def has_access(user_id):
    return is_admin(user_id)


def main_keyboard():
    return ReplyKeyboardMarkup(
        [[BTN_BROADCAST]],
        resize_keyboard=True
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id

    if not has_access(user_id):
        await update.message.reply_text("У тебя нет доступа.")
        return

    if chat.type != "private":
        await update.message.reply_text("Бот работает ✅")
        return

    await update.message.reply_text(
        "Выбери действие:",
        reply_markup=main_keyboard()
    )


async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id

    if not has_access(user_id):
        await update.message.reply_text("У тебя нет доступа.")
        return

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Эту команду нужно писать в группе.")
        return

    groups.add(chat.id)
    save_groups(groups)

    await update.message.reply_text("Группа добавлена ✅")


async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id

    if not has_access(user_id):
        await update.message.reply_text("У тебя нет доступа.")
        return

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Эту команду нужно писать в группе.")
        return

    if chat.id in groups:
        groups.remove(chat.id)
        save_groups(groups)
        await update.message.reply_text("Группа удалена из рассылки ✅")
    else:
        await update.message.reply_text("Этой группы нет в списке рассылки.")


async def check_group_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.my_chat_member:
        return

    chat = update.effective_chat
    user = update.my_chat_member.from_user

    if not is_admin(user.id):
        await context.bot.leave_chat(chat.id)


async def groups_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(f"Сохранено групп: {len(groups)}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        f"📊 Статистика\n\n"
        f"👥 Групп в рассылке: {len(groups)}\n"
        f"👤 Админов: {len(ADMIN_IDS)}\n"
        f"💾 Файл групп: {GROUPS_FILE}"
    )


async def send_broadcast(context: ContextTypes.DEFAULT_TYPE, user_id: int, from_chat_id: int, message_id: int):
    success = 0
    failed = 0

    try:
        msg = await context.bot.forward_message(
            chat_id=user_id,
            from_chat_id=from_chat_id,
            message_id=message_id
        )
        await context.bot.delete_message(chat_id=user_id, message_id=msg.message_id)
    except Exception:
        msg = None

    for group_id in groups:
        try:
            original_message = pending_messages.get(user_id)

            if original_message and original_message.text:
                final_text = original_message.text

                if BROADCAST_FOOTER.strip():
                    final_text = f"{final_text}\n\n{BROADCAST_FOOTER.strip()}"

                await context.bot.send_message(
                    chat_id=group_id,
                    text=final_text
                )
            else:
                await context.bot.copy_message(
                    chat_id=group_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id
                )

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

    if not has_access(user_id):
        await update.message.reply_text("У тебя нет доступа.")
        return

    if update.message.text == BTN_BROADCAST:
        user_states[user_id] = "waiting_message"
        await update.message.reply_text(
            "Отправь сообщение для рассылки.\n\n"
            "Можно отправить текст, эмодзи, фото, стикер, видео, документ или GIF."
        )
        return

    if user_states.get(user_id) == "waiting_message":
        user_states.pop(user_id, None)

        await update.message.reply_text("Отправляю рассылку...")

        await send_broadcast(
            context=context,
            user_id=user_id,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
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

    success = 0
    failed = 0

    for group_id in groups:
        try:
            await context.bot.send_message(chat_id=group_id, text=text)
            success += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"Рассылка отправлена ✅\nОтправлено: {success}\nОшибок: {failed}",
        reply_markup=main_keyboard()
    )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addgroup", add_group))
    app.add_handler(CommandHandler("removegroup", remove_group))
    app.add_handler(CommandHandler("groups", groups_count))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(
        ChatMemberHandler(
            check_group_access,
            ChatMemberHandler.MY_CHAT_MEMBER
        )
    )

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            handle_private_message
        )
    )

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()