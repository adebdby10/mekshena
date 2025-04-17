import os
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Ganti dengan API ID dan API Hash Anda yang bisa didapatkan dari https://my.telegram.org/auth
api_id = '23416622'
api_hash = 'd1bc12a03ea26416b38b4616a36112b0'

# Folder tempat session disimpan
SESSION_FOLDER = 'eww_sessions/'

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

# Fungsi untuk memeriksa status semua session dalam folder dan menghitung session aktif
def check_all_sessions_status():
    # Ambil semua file session yang ada di folder
    sessions = [f for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]
    total_sessions = len(sessions)  # Menghitung jumlah file session
    active_count = 0  # Inisialisasi penghitung session aktif

    print(f"Total sessions found: {total_sessions}\n")

    for session_name in sessions:
        status = check_session_status(session_name)
        print(f"Session {session_name} is {status}.")

        # Hitung jumlah session yang aktif
        if status == "active":
            active_count += 1

    print(f"\nTotal active sessions: {active_count}")

if __name__ == "__main__":
    check_all_sessions_status()
