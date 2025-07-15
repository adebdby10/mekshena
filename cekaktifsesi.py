import os
import gc
import time
import json
import logging
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    AuthKeyUnregisteredError,
    FloodWaitError,
    PhoneNumberBannedError,
    RPCError,
)

# Konfigurasi
api_id = 23520639
api_hash = 'bcbc7a22cde8fa2ba7d1baad086086ca'
SESSION_FOLDER = 'a38_sessions'
OUTPUT_TXT = 'a38_sessions.txt'
OUTPUT_JSON = 'a38_sessions.json'

# Setup logging
logging.basicConfig(
    filename='session_check.log',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)

def get_file_paths(session_name):
    """Mendeteksi semua file yang terkait dengan session_name di folder."""
    paths = []
    for f in os.listdir(SESSION_FOLDER):
        if f.startswith(session_name):
            full_path = os.path.join(SESSION_FOLDER, f)
            if os.path.isfile(full_path):
                paths.append(full_path)
    return paths

def backdate_file_mod_time(paths, days=1):
    """Mengubah timestamp modifikasi file menjadi mundur beberapa hari."""
    for path in paths:
        try:
            stat = os.stat(path)
            new_time = stat.st_mtime - (days * 86400)
            os.utime(path, (stat.st_atime, new_time))
            logging.info(f"✔️ Backdated: {path}")
        except Exception as e:
            logging.warning(f"❌ Gagal backdate {path}: {e}")

def delete_session_files(session_name):
    """Menghapus semua file yang berkaitan dengan session tertentu."""
    deleted = False
    paths = get_file_paths(session_name)
    for path in paths:
        try:
            os.remove(path)
            logging.info(f"🗑️ Deleted: {path}")
            deleted = True
        except Exception as e:
            logging.error(f"❌ Gagal menghapus {path}: {e}")
    return deleted

def check_session_status(session_name, active_numbers):
    client = None
    session_path = os.path.join(SESSION_FOLDER, session_name)

    try:
        client = TelegramClient(session_path, api_id, api_hash)
        client.connect()

        if not client.is_user_authorized():
            return "inactive"

        try:
            client.start()
        except SessionPasswordNeededError:
            logging.warning(f"🔐 Session {session_name} butuh 2FA, dianggap 'corrupt'")
            return "corrupt"

        me = client.get_me()
        if me and me.phone:
            phone = f"+{me.phone}"
            active_numbers.append(phone)
            logging.info(f"📱 Active: {phone}")

        return "active"

    except (AuthKeyUnregisteredError, PhoneNumberBannedError) as e:
        logging.warning(f"🚫 Session {session_name} error fatal: {e}")
        return "corrupt"
    except FloodWaitError as e:
        logging.error(f"⚠️ FloodWaitError: Tunggu {e.seconds} detik")
        time.sleep(e.seconds + 5)
        return "retry"
    except RPCError as e:
        logging.warning(f"⚠️ RPCError lain: {e}")
        return "corrupt"
    except Exception as e:
        logging.error(f"❌ Error saat cek session {session_name}: {e}")
        return "corrupt"
    finally:
        if client and client.is_connected():
            client.disconnect()
        gc.collect()

def save_active_numbers(active_numbers):
    try:
        with open(OUTPUT_TXT, 'w') as txt_file:
            for number in active_numbers:
                txt_file.write(number + '\n')
        with open(OUTPUT_JSON, 'w') as json_file:
            json.dump(active_numbers, json_file, indent=2)
        logging.info(f"✅ Nomor aktif disimpan ke {OUTPUT_TXT} dan {OUTPUT_JSON}")
    except Exception as e:
        logging.error(f"❌ Gagal menyimpan file output: {e}")

def check_all_sessions_status():
    sessions = {
        f.replace('.session', '')
        for f in os.listdir(SESSION_FOLDER)
        if f.endswith('.session') and os.path.isfile(os.path.join(SESSION_FOLDER, f))
    }

    total_active = 0
    total_deleted = 0
    active_numbers = []

    logging.info(f"🚀 Memulai pengecekan {len(sessions)} sesi...")

    for idx, session_name in enumerate(sorted(sessions), start=1):
        paths = get_file_paths(session_name)
        status = check_session_status(session_name, active_numbers)
        print(f"[{idx}/{len(sessions)}] Session '{session_name}': {status.upper()}")

        if status == "active":
            total_active += 1
            backdate_file_mod_time(paths, days=1)
        elif status == "retry":
            print("⏳ Delay sementara karena FloodWait...")
            continue
        else:
            if delete_session_files(session_name):
                total_deleted += 1

        time.sleep(1.0)  # Delay antar cek agar aman

    # Simpan hasil
    save_active_numbers(active_numbers)

    print("\n========== SUMMARY ==========")
    print(f"✅ Total Active Sessions  : {total_active}")
    print(f"🗑️ Total Deleted Sessions : {total_deleted}")
    print(f"📁 File Nomor Aktif       : {OUTPUT_TXT}, {OUTPUT_JSON}")
    print("================================")

    if active_numbers:
        print("\n📱 Active Phone Numbers:")
        for num in active_numbers:
            print(f" - {num}")

if __name__ == "__main__":
    check_all_sessions_status()
