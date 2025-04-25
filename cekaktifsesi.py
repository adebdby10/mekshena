import os
import shutil
import gc
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

api_id = '23520639'
api_hash = 'bcbc7a22cde8fa2ba7d1baad086086ca'

SESSION_FOLDER = 'login3'
ACTIVE_FOLDER = os.path.join(SESSION_FOLDER, 'active')
INACTIVE_FOLDER = os.path.join(SESSION_FOLDER, 'inactive')
CORRUPT_FOLDER = os.path.join(SESSION_FOLDER, 'corrupt')

# Buat folder tujuan jika belum ada
for folder in [ACTIVE_FOLDER, INACTIVE_FOLDER, CORRUPT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

def move_session_files(session_name, target_folder):
    base_name = os.path.join(SESSION_FOLDER, session_name)
    moved_files = 0
    for ext in ['', '.session-journal', '.session']:
        file_path = base_name + ext
        if os.path.exists(file_path):
            try:
                shutil.move(file_path, os.path.join(target_folder, session_name + ext))
                print(f"Moved: {file_path} ➜ {target_folder}")
                moved_files += 1
            except Exception as e:
                print(f"❌ Gagal memindahkan {file_path}: {e}")
    return moved_files > 0

def check_session_status(session_name):
    client = None
    try:
        client = TelegramClient(os.path.join(SESSION_FOLDER, session_name), api_id, api_hash)
        client.connect()

        if not client.is_user_authorized():
            return "inactive"

        try:
            client.start()
        except SessionPasswordNeededError:
            return "corrupt"

        return "active"
    except Exception as e:
        print(f"Error while checking session {session_name}: {e}")
        return "corrupt"
    finally:
        if client and client.is_connected():
            client.disconnect()
        gc.collect()

def check_all_sessions_status():
    sessions = [
        f.replace('.session', '')
        for f in os.listdir(SESSION_FOLDER)
        if f.endswith('.session') and os.path.isfile(os.path.join(SESSION_FOLDER, f))
    ]

    total_active = 0
    total_inactive = 0
    total_corrupt = 0

    for session_name in set(sessions):  # hindari duplikat
        status = check_session_status(session_name)
        print(f"Session {session_name} is {status}.")

        if status == "active":
            if move_session_files(session_name, ACTIVE_FOLDER):
                total_active += 1
        elif status == "inactive":
            if move_session_files(session_name, INACTIVE_FOLDER):
                total_inactive += 1
        elif status == "corrupt":
            if move_session_files(session_name, CORRUPT_FOLDER):
                total_corrupt += 1

    print("\n========== SUMMARY ==========")
    print(f"Total Active Sessions   : {total_active}")
    print(f"Total Inactive Sessions : {total_inactive}")
    print(f"Total Corrupt Sessions  : {total_corrupt}")
    print("================================")

if __name__ == "__main__":
    check_all_sessions_status()
