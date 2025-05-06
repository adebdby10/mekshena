import os
import gc
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

api_id = '23520639'
api_hash = 'bcbc7a22cde8fa2ba7d1baad086086ca'

SESSION_FOLDER = 'a9_sessions'

def delete_session_files(session_name):
    base_name = os.path.join(SESSION_FOLDER, session_name)
    deleted = False
    for ext in ['', '.session-journal', '.session']:
        file_path = base_name + ext
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Deleted: {file_path}")
                deleted = True
            except Exception as e:
                print(f"❌ Gagal menghapus {file_path}: {e}")
    return deleted

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
    total_deleted = 0

    for session_name in set(sessions):  # hindari duplikat
        status = check_session_status(session_name)
        print(f"Session {session_name} is {status}.")

        if status == "active":
            total_active += 1
        else:
            if delete_session_files(session_name):
                total_deleted += 1

    print("\n========== SUMMARY ==========")
    print(f"Total Active Sessions  : {total_active}")
    print(f"Total Deleted Sessions : {total_deleted}")
    print("================================")

if __name__ == "__main__":
    check_all_sessions_status()
