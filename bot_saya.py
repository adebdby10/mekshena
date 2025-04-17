import json
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext
import logging

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token
bot_token = '7909589038:AAG-_MOyqyDDOMkf9IoXsJjqjX5rVIfV1b8'

# === Fungsi untuk Memuat Daftar Sesi Login ===
def load_sessions():
    try:
        with open('sessions.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# === Fungsi untuk Mengirim Tombol Daftar Sesi ===
async def send_sessions_button(update: Update, context: CallbackContext):
    sessions = load_sessions()
    if sessions:
        keyboard = {
            "inline_keyboard": [
                [{"text": f"Nomor {num}", "callback_data": f"show_sessions"}] for num in sessions
            ]
        }
        await update.message.reply_text(
            "Berikut adalah daftar nomor yang sudah login:",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            "❌ Belum ada nomor yang login."
        )

# === Fungsi untuk Mengirim Status Login Nomor ===
async def status(update: Update, context: CallbackContext):
    try:
        phone_number = context.args[0]  # Ambil nomor telepon dari argumen
        sessions = load_sessions()
        if phone_number in sessions:
            status_message = f"{phone_number} sudah login."
        else:
            status_message = f"{phone_number} belum login."
    except IndexError:
        status_message = "❌ Silakan beri nomor telepon setelah perintah /status."

    await update.message.reply_text(status_message)

# === Fungsi untuk Menampilkan Perintah Bantuan ===
async def help(update: Update, context: CallbackContext):
    help_message = (
        "Perintah yang tersedia:\n"
        "/start: Mulai bot\n"
        "/sessions: Lihat sesi yang sudah login\n"
        "/status <nomor_telepon>: Cek status login nomor\n"
        "/login <nomor_telepon>: Mulai proses login"
    )
    await update.message.reply_text(help_message)

# === Fungsi Utama untuk Menghubungkan Bot dan Handler ===
async def main():
    # Inisialisasi Application
    application = Application.builder().token(bot_token).build()

    # Menambahkan handler untuk command
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sessions", send_sessions_button))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help))

    # Mulai polling
    await application.run_polling()

# === Fungsi untuk Sambutan Awal ===
async def start(update: Update, context: CallbackContext):
    welcome_message = "Selamat datang! Gunakan perintah /help untuk melihat daftar perintah yang tersedia."
    await update.message.reply_text(welcome_message)

if __name__ == "__main__":
    # Inisialisasi Application
    application = Application.builder().token(bot_token).build()

    # Menambahkan handler untuk command
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sessions", send_sessions_button))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help))

    # Menjalankan polling secara langsung
    application.run_polling()

