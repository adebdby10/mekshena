import os
import time
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Ganti dengan API ID dan API Hash Anda yang bisa didapatkan dari https://my.telegram.org/auth
api_id = '23416622'
api_hash = 'd1bc12a03ea26416b38b4616a36112b0'

# Folder tempat session disimpan
SESSION_FOLDER = 'sessions/'

# Fungsi untuk mengecek status session dan status koneksi
def check_session_status(session_name):
    client = None
    try:
        # Inisialisasi client Telegram dengan session
        client = TelegramClient(os.path.join(SESSION_FOLDER, session_name), api_id, api_hash)
        client.connect()

        if not client.is_user_authorized():
            return "inactive"
        
        # Cek jika password diperlukan (artinya session mungkin corrupt)
        try:
            client.start()
        except SessionPasswordNeededError:
            return "corrupt"
        
        return "active"
    except Exception as e:
        print(f"Error while checking session {session_name}: {e}")
        return "corrupt"
    finally:
        if client:
            if client.is_connected():
                client.disconnect()

# Fungsi untuk menghapus session yang tidak aktif atau corrupt
def delete_session(session_name):
    session_path = os.path.join(SESSION_FOLDER, session_name)
    try:
        if os.path.exists(session_path):
            os.remove(session_path)
            print(f"Session {session_name} deleted.")
    except PermissionError as e:
        print(f"Permission error while deleting session {session_name}: {e}")
        # Tunggu beberapa detik dan coba lagi
        time.sleep(2)
        try:
            os.remove(session_path)
            print(f"Session {session_name} deleted after retry.")
        except Exception as ex:
            print(f"Failed to delete session {session_name} after retry: {ex}")

# Fungsi untuk memeriksa dan menghapus session
def clean_sessions():
    # Ambil semua file session yang ada di folder
    sessions = [f for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]

    for session_name in sessions:
        status = check_session_status(session_name)

        if status == "inactive" or status == "corrupt":
            # Hapus session file yang corrupt atau tidak aktif
            delete_session(session_name)

if __name__ == "__main__":
    clean_sessions()
