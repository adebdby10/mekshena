import os
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.types import User
import logging

API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca'


# Definisikan status Conversation
SET_PASSWORD = range(1)

# Fungsi untuk memulai proses pengaturan password
async def start_set_password(update: Update, context: CallbackContext):
    phone_number = context.user_data.get('phone_number')
    session_path = context.user_data.get('session_path')

    if not session_path:
        # Tentukan path default untuk session jika tidak ada
        session_path = os.path.join(os.getcwd(), 'login1', str(phone_number))
        # Pastikan folder untuk session ada
        if not os.path.exists(os.path.dirname(session_path)):
            os.makedirs(os.path.dirname(session_path))
        
        # Simpan session_path kembali ke user_data
        context.user_data['session_path'] = session_path

    if not session_path:
        await update.callback_query.message.reply_text("❌ Session tidak ditemukan.")
        return

    try:
        # Mulai TelegramClient
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.start()

        # Pastikan akun membutuhkan password untuk login
        try:
            await client.get_me()
        except SessionPasswordNeededError:
            await update.callback_query.message.reply_text(
                "🔐 Masukkan password baru untuk akun ini:\n(Pastikan Anda mengetahui password yang akan diubah)"
            )
            return SET_PASSWORD
        except Exception as e:
            logging.error(f"Error saat memulai client: {e}")
            await update.callback_query.message.reply_text("❌ Gagal memulai sesi.")
            return

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.callback_query.message.reply_text(f"❌ Terjadi kesalahan: {e}")
        return

# Fungsi untuk menerima konfirmasi password baru
async def receive_confirmation(update: Update, context: CallbackContext):
    new_password = update.message.text
    session_path = context.user_data.get('session_path')

    if not session_path:
        await update.message.reply_text("❌ Session tidak ditemukan.")
        return ConversationHandler.END

    try:
        # Memulai client Telethon
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.start()

        # Atur password akun (contoh: menggunakan fungsi autentikasi Telegram)
        await client(function.account.UpdatePasswordSettings(password=new_password))

        await update.message.reply_text("✅ Password telah berhasil diubah!")

        await client.disconnect()

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Gagal mengubah password: {e}")

    return ConversationHandler.END

# Fungsi untuk membatalkan proses pengaturan password
async def cancel_password(update: Update, context: CallbackContext):
    await update.message.reply_text("❌ Pengaturan password dibatalkan.")
    return ConversationHandler.END
