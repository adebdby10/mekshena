import os
import asyncio
from telethon import TelegramClient

# Konfigurasi API
API_ID = 23416622
API_HASH = 'd1bc12a03ea26416b38b4616a36112b0'

# Folder session
SESSION_FOLDER = os.path.join(os.path.dirname(__file__), 'sessions')  # Atau eww_sessions, tergantung di mana kamu simpan
os.makedirs(SESSION_FOLDER, exist_ok=True)

async def logout_other_devices(phone_number: str):
    session_file = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_file):
        print(f"[❌] Session untuk {phone_number} tidak ditemukan.")
        return

    try:
        client = TelegramClient(session_file, API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            print(f"[❌] Belum login untuk {phone_number}.")
            return

        # Logout dari semua perangkat (selain current session)
        result = await client(functions.account.ResetAuthorizationRequest(hash=0))
        print(f"[✅] Semua perangkat lama untuk {phone_number} telah logout.")
        
        await client.disconnect()

    except Exception as e:
        print(f"[⚠️] Gagal logout perangkat lama: {e}")

# Contoh penggunaan
if __name__ == "__main__":
    phone = input("Masukkan nomor telepon (contoh: +628xxxxxx): ")
    asyncio.run(logout_other_devices(phone))
