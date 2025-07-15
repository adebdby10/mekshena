import os
import shutil
from telethon.sync import TelegramClient

# === KONFIGURASI ===
SESSION_DIR = 'a32_sessions/without_2fa'
API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca'

# Buat folder 1–9 dan id_unik
for i in range(1, 10):
    os.makedirs(str(i), exist_ok=True)
os.makedirs('id_unik', exist_ok=True)

def get_user_id(session_path):
    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        client.connect()
        if not client.is_user_authorized():
            client.disconnect()
            return None
        user = client.get_me()
        client.disconnect()
        return user.id
    except Exception as e:
        print(f"[ERROR] {session_path} -> {e}")
        return None

# Proses semua file .session
for file in os.listdir(SESSION_DIR):
    if not file.endswith('.session'):
        continue

    full_path = os.path.join(SESSION_DIR, file)
    user_id = get_user_id(full_path)

    if user_id is None:
        continue

    str_id = str(user_id)

    if len(str_id) == 10 and str_id[0] in '123456789':
        folder = str_id[0]
    elif len(str_id) < 10:
        folder = 'id_unik'
    else:
        print(f"[SKIP] {file} -> user_id tidak sesuai kriteria: {user_id}")
        continue

    shutil.move(full_path, os.path.join(folder, file))
    print(f"[MOVED] {file} -> {folder}/")
