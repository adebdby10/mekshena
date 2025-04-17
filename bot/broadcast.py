from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telethon.sync import TelegramClient
from telethon.tl.types import Channel
import os

# Fungsi untuk broadcast pesan ke grup yang diikuti oleh session
async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    # Ambil pesan dari user
    message_to_broadcast = update.callback_query.message.text.split('\n')[-1]  # Ambil pesan terakhir pada text

    try:
        # Buat client sementara
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.start()

        # Dapatkan daftar grup yang diikuti
        dialogs = await client.get_dialogs()
        groups = [dialog for dialog in dialogs if isinstance(dialog.entity, Channel) and dialog.entity.megagroup]

        # Kirim pesan ke setiap grup
        sent_count = 0
        for group in groups:
            try:
                await client.send_message(group.entity.id, message_to_broadcast)
                sent_count += 1
            except Exception as e:
                print(f"⚠️ Gagal mengirim ke grup {group.title}: {e}")

        await client.disconnect()

        # Tampilkan hasil
        if sent_count > 0:
            await update.callback_query.message.reply_text(f"✅ Pesan berhasil disebarkan ke {sent_count} grup.")
        else:
            await update.callback_query.message.reply_text("⚠️ Tidak ada grup yang dapat diakses atau pesan gagal dikirim.")

    except Exception as e:
        await update.callback_query.message.reply_text(f"⚠️ Terjadi kesalahan: {e}")

