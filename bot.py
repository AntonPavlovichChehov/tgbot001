import re
from datetime import datetime
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
BALANCE_FILE = "/data/balance.json"

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
def load_balance():
    if not os.path.exists(BALANCE_FILE):
        return {}

    with open(BALANCE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_balance(data):
    with open(BALANCE_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


balances = load_balance()


def fmt_amount(value):
    if value == int(value):
        return str(int(value))
    return str(value)

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

async def send_broadcast(context: ContextTypes.DEFAULT_TYPE, user_id: int, from_chat_id: int, message_id: int, text=None):
    success = 0
    failed = 0

    for group_id in groups:
        try:
            if text:
                final_text = text

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
            context,
            user_id,
            update.effective_chat.id,
            update.message.message_id,
            text=update.message.text
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

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text("🏓 Pong\nБот работает")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    text = (
        f"📊 Статистика\n\n"
        f"Групп в базе: {len(groups)}\n"
        f"Админов: {len(ADMIN_IDS)}"
    )

    await update.message.reply_text(text)

async def change_balance(update: Update, context: ContextTypes.DEFAULT_TYPE, sign: int):
    if update.effective_chat.type not in ["group", "supergroup"]:
        return

    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        return

    amount_text = context.args[0].replace(",", ".")

    try:
        amount = float(amount_text)
    except ValueError:
        return

    amount = amount * sign
    comment = " ".join(context.args[1:]) or "Без комментария"

    chat_id = str(update.effective_chat.id)

    if chat_id not in balances:
        balances[chat_id] = {
            "balance": 0,
            "history": []
        }

    balances[chat_id]["balance"] += amount
    balances[chat_id]["history"].append({
        "amount": amount,
        "comment": comment,
        "user": update.effective_user.id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    balances[chat_id]["history"] = balances[chat_id]["history"][-100:]

    save_balance(balances)

    await update.message.reply_text(
        f"✅ Операция сохранена\n\n"
        f"{'➕' if amount > 0 else '➖'} {fmt_amount(abs(amount))}\n"
        f"📝 {comment}\n\n"
        f"💰 Баланс: {fmt_amount(balances[chat_id]['balance'])}"
    )


async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await change_balance(update, context, 1)


async def sub_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await change_balance(update, context, -1)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        return

    if not is_admin(update.effective_user.id):
        return

    chat_id = str(update.effective_chat.id)
    balance_value = balances.get(chat_id, {}).get("balance", 0)

    await update.message.reply_text(f"💰 Баланс группы: {fmt_amount(balance_value)}")


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        return

    if not is_admin(update.effective_user.id):
        return

    chat_id = str(update.effective_chat.id)
    history_list = balances.get(chat_id, {}).get("history", [])[-10:]

    if not history_list:
        await update.message.reply_text("📋 История пустая.")
        return

    text = "📋 Последние операции:\n\n"

    for item in history_list:
        amount = item["amount"]
        icon = "➕" if amount > 0 else "➖"
        text += f"{icon} {fmt_amount(abs(amount))} — {item['comment']}\n"

    await update.message.reply_text(text)


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        return

    if not is_admin(update.effective_user.id):
        return

    chat_id = str(update.effective_chat.id)
    data = balances.get(chat_id, {"balance": 0, "history": []})

    income = sum(x["amount"] for x in data["history"] if x["amount"] > 0)
    expense = sum(abs(x["amount"]) for x in data["history"] if x["amount"] < 0)

    await update.message.reply_text(
        f"📊 Финансовый отчёт группы\n\n"
        f"💰 Баланс: {fmt_amount(data['balance'])}\n"
        f"➕ Поступления: {fmt_amount(income)}\n"
        f"➖ Расходы: {fmt_amount(expense)}\n"
        f"📋 Операций: {len(data['history'])}"
    )


async def clearbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        return

    if not is_admin(update.effective_user.id):
        return

    chat_id = str(update.effective_chat.id)

    balances[chat_id] = {
        "balance": 0,
        "history": []
    }

    save_balance(balances)

    await update.message.reply_text("🧹 Баланс и история группы очищены.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addgroup", add_group))
    app.add_handler(CommandHandler("removegroup", remove_group))
    app.add_handler(CommandHandler("groups", groups_count))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("stats", stats))

    app.add_handler(
        ChatMemberHandler(
            check_group_access,
            ChatMemberHandler.MY_CHAT_MEMBER
        )
    )

    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("clearbalance", clearbalance))

    app.add_handler(CommandHandler("add", add_balance))
    app.add_handler(CommandHandler("sub", sub_balance))

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