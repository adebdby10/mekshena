import os
import shutil
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

# --- Konfigurasi ---
API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca' # Ganti dengan API HASH Anda

SESSION_DIR = "6"
WITH_2FA_DIR = "6/with_2fa"
WITHOUT_2FA_DIR = "6/without_2fa"

os.makedirs(WITH_2FA_DIR, exist_ok=True)
os.makedirs(WITHOUT_2FA_DIR, exist_ok=True)

def check_session_2fa(session_name):
    session_path = os.path.join(SESSION_DIR, session_name)
    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        client.connect()

        if not client.is_user_authorized():
            print(f"[❌] {session_name}: Belum login")
            client.disconnect()
            return None

        try:
            # Start akan error kalau ada 2FA
            client.start()
            print(f"[✅] {session_name}: TANPA 2FA")
            client.disconnect()
            return False
        except SessionPasswordNeededError:
            print(f"[🔒] {session_name}: DENGAN 2FA")
            client.disconnect()
            return True

    except Exception as e:
        print(f"[ERROR] {session_name}: {e}")
        return None

def process_all_sessions():
    for file in os.listdir(SESSION_DIR):
        if file.endswith(".session"):
            result = check_session_2fa(file)
            src_path = os.path.join(SESSION_DIR, file)

            if result is True:
                shutil.move(src_path, os.path.join(WITH_2FA_DIR, file))
            elif result is False:
                shutil.move(src_path, os.path.join(WITHOUT_2FA_DIR, file))
            # Jika None (error), tidak dipindahkan

if __name__ == "__main__":
    process_all_sessions()
