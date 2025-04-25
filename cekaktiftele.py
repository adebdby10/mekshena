import os
import glob
import time
import requests
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Ganti dengan API ID dan API Hash dari my.telegram.org
api_id = '26763615'
api_hash = '4d8aa7c999f425c489422548d1db0bd7'

# Bot Telegram kamu
BOT_TOKEN = '8033198485:AAG5-a8uZ3AhjRNNIUqmR4VkePTQd7j7ibA'
CHAT_ID = '7125327252'  # dari @userinfobot

# Folder session
SESSION_FOLDER = 'login3'

def send_to_bot(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        res = requests.post(url, data=payload)
        if res.status_code == 200:
            print("📩 Hasil dikirim ke bot.")
        else:
            print(f"⚠️ Gagal kirim ke bot. Status: {res.status_code}")
    except Exception as e:
        print(f"❌ Gagal kirim pesan: {e}")

def delete_session_files(session_name):
    session_base = os.path.splitext(session_name)[0]
    pattern = os.path.join(SESSION_FOLDER, f"{session_base}*")

    deleted_files = []
    for filepath in glob.glob(pattern):
        try:
            os.remove(filepath)
            deleted_files.append(os.path.basename(filepath))
        except Exception as e:
            print(f"❌ Gagal hapus {filepath}: {e}")

    if deleted_files:
        print(f"🗑️ Menghapus {', '.join(deleted_files)}")
    else:
        print(f"⚠️ Tidak ada file dihapus untuk {session_base}")

def check_session_registration(session_name):
    session_path = os.path.join(SESSION_FOLDER, session_name)
    client = TelegramClient(session_path, api_id, api_hash)
    try:
        client.connect()

        if not client.is_user_authorized():
            print(f"⚠️ {session_name} tidak terdaftar. Menghapus...")
            return 'not_registered'
        
        return 'registered'

    except Exception as e:
        print(f"❌ Error dengan {session_name}: {e}")
        return 'error'

    finally:
        if client.is_connected():
            client.disconnect()
        time.sleep(0.5)  # delay untuk memastikan file dilepas

def check_all_sessions_registration():
    if not os.path.exists(SESSION_FOLDER):
        print(f"❌ Folder {SESSION_FOLDER} tidak ditemukan.")
        return

    sessions = [f for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]

    total = len(sessions)
    registered_list = []
    registered = not_registered = errors = 0

    print(f"\n🔍 Menemukan {total} sesi di folder '{SESSION_FOLDER}':\n")

    for session in sessions:
        status = check_session_registration(session)

        if status == 'registered':
            print(f"✅ {session} TERDAFTAR.")
            registered += 1
            registered_list.append(session)
        else:
            delete_session_files(session)
            if status == 'not_registered':
                print(f"⚠️ {session} tidak terdaftar dan DIHAPUS.")
                not_registered += 1
            else:
                print(f"❌ {session} error dan DIHAPUS.")
                errors += 1

    # Ringkasan pesan
    result_text = f"📊 Ringkasan:\n"
    result_text += f"✔️ Terdaftar     : {registered}\n"
    result_text += f"❌ Tidak daftar  : {not_registered}\n"
    result_text += f"⚠️ Error session: {errors}\n"
    result_text += f"🧮 Total sesi    : {total}"

    send_to_bot(result_text)

    print("\n📊 Ringkasan:")
    print(f"✔️ Terdaftar     : {registered}")
    print(f"❌ Tidak daftar  : {not_registered}")
    print(f"⚠️ Error session: {errors}")
    print(f"🧮 Total sesi    : {total}")

    # Cek apakah masih ada sisa file
    leftover_files = os.listdir(SESSION_FOLDER)
    if leftover_files:
        print("\n📁 Sisa file di folder:")
        for f in leftover_files:
            print("•", f)
    else:
        print("\n🧹 Folder sesi bersih!")

if __name__ == "__main__":
    check_all_sessions_registration()
