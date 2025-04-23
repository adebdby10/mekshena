from telethon import TelegramClient, errors
import os
import asyncio
from telegram.constants import ParseMode
from telegram import Update
from telegram.ext import ContextTypes
from telethon.tl.custom.button import Button

# Folder tempat session disimpan
SESSION_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'broadcast'))

async def broadcast_via_dialog_handler(update, context, phone_number):
    query = update.callback_query
    await query.answer()
    
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    
    if not os.path.exists(session_path):
        await query.message.reply_text(
            f"❌ Session tidak ditemukan untuk:\n`{phone_number}`\n\nCek path:\n`{session_path}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await query.message.reply_text(f"✅ Session ditemukan untuk {phone_number}. Mulai broadcast...")

    # Pesan dan link yang aman
    pesan_broadcast = "📢 Hai, ini adalah pesan dari akun kami. Semoga harimu menyenangkan!\n\n" \
                      "Klik di sini untuk mengunjungi website kami: [Kunjungi Website](https://www.youtube.com/watch?v=2vHziVI2cOk)"
    
    # Menggunakan session Telethon untuk kirim pesan
    client = TelegramClient(session_path, context.bot_data['api_id'], context.bot_data['api_hash'])
    await client.connect()

    if not await client.is_user_authorized():
        await query.message.reply_text("❌ Akun belum login.")
        return

    try:
        count = 0
        async for dialog in client.iter_dialogs():
            entity = dialog.entity

            # Filter: skip bot, channel, grup
            if getattr(entity, 'bot', False) or entity.id < 0:
                continue

            try:
                # Kirim pesan teks dengan link yang aman
                await client.send_message(
                    entity,
                    pesan_broadcast,
                    parse_mode=ParseMode.MARKDOWN  # Gunakan Markdown untuk menampilkan link
                )
                print(f"✅ Terkirim ke: {entity.id} - {entity.username or entity.first_name}")
                count += 1
                await asyncio.sleep(2.5)  # Delay aman
            except errors.FloodWaitError as e:
                print(f"⏳ FloodWait {e.seconds} detik.")
                await asyncio.sleep(e.seconds + 5)
            except Exception as e:
                print(f"❌ Gagal kirim ke {entity.id}: {e}")

        await query.message.reply_text(f"✅ Broadcast selesai.\nTotal terkirim: {count} user.")
    finally:
        await client.disconnect()
