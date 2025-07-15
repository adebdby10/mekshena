import os
import shutil
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca'

SESSION_FOLDER = "5"
OUTPUT_FOLDER_1 = "5"
OUTPUT_FOLDER_2 = "5"

# Buat folder output jika belum ada
os.makedirs(OUTPUT_FOLDER_1, exist_ok=True)
os.makedirs(OUTPUT_FOLDER_2, exist_ok=True)

for filename in os.listdir(SESSION_FOLDER):
    if not filename.endswith(".session"):
        continue

    session_path = os.path.join(SESSION_FOLDER, filename)

    try:
        client = TelegramClient(session_path.replace(".session", ""), API_ID, API_HASH, system_version="4.16.30-vxRay")
        client.connect()
        if not client.is_user_authorized():
            print(f"[SKIP] {filename} tidak login.")
            client.disconnect()
            continue

        user = client.get_me()
        user_id = user.id

        if 5000000000 <= user_id <= 5599999999:
            shutil.move(session_path, os.path.join(OUTPUT_FOLDER_1, filename))
            print(f"[50-55] {filename} → {OUTPUT_FOLDER_1}")
        elif 5600000000 <= user_id <= 5999999999:
            shutil.move(session_path, os.path.join(OUTPUT_FOLDER_2, filename))
            print(f"[56-59] {filename} → {OUTPUT_FOLDER_2}")
        else:
            print(f"[LEWAT] {filename} ID: {user_id}")

        client.disconnect()
    except Exception as e:
        print(f"[ERROR] {filename}: {e}")
