import os
import time
import gc
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.account import GetAuthorizationsRequest

API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d1baad086086ca'

SOURCE_FOLDER = "7"
FOLDER_WITH_2FA = "7/with_2fa"
FOLDER_NO_2FA = "7/no_2fa"
FOLDER_ERROR = "7/error"

# Buat folder
os.makedirs(FOLDER_WITH_2FA, exist_ok=True)
os.makedirs(FOLDER_NO_2FA, exist_ok=True)
os.makedirs(FOLDER_ERROR, exist_ok=True)

def move_session(session_file, target_folder, status):
    source = os.path.join(SOURCE_FOLDER, session_file)
    target = os.path.join(target_folder, session_file)

    for attempt in range(3):
        try:
            if os.path.exists(target):
                os.remove(target)
            os.rename(source, target)
            print(f"[{status}] {session_file}")
            return
        except Exception as e:
            if attempt < 2:
                time.sleep(0.5)
            else:
                print(f"[❌ MOVE ERROR] {session_file} → {e}")

def classify_session(session_file):
    session_path = os.path.join(SOURCE_FOLDER, session_file)
    client = None
    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        client.connect()

        if not client.is_user_authorized():
            move_session(session_file, FOLDER_ERROR, "⛔ UNAUTHORIZED")
            return

        try:
            client(GetAuthorizationsRequest())
            move_session(session_file, FOLDER_NO_2FA, "✅ NO 2FA")
        except SessionPasswordNeededError:
            move_session(session_file, FOLDER_WITH_2FA, "🔒 WITH 2FA")
        except Exception as e:
            move_session(session_file, FOLDER_ERROR, f"‼️ ERROR: {e}")

    except Exception as e:
        move_session(session_file, FOLDER_ERROR, f"‼️ OPEN ERROR: {e}")

    finally:
        if client:
            client.disconnect()
            del client
        gc.collect()  # Paksa release file lock
        time.sleep(0.2)  # Delay kecil agar Windows melepaskan file lock

def main():
    files = [f for f in os.listdir(SOURCE_FOLDER) if f.endswith(".session")]
    print(f"\n🔍 Total sessions found: {len(files)}\n")

    for session_file in files:
        classify_session(session_file)

if __name__ == "__main__":
    main()
