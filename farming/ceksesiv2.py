import os
import gc
import time
import json
import logging
import shutil
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    AuthKeyUnregisteredError,
    FloodWaitError,
    PhoneNumberBannedError,
    RPCError,
)
from telethon.tl.functions.account import GetPasswordRequest

# Konfigurasi
api_id = 29564591
api_hash = '99d943dcb43f77dd61c9b020105a541b'
SESSION_FOLDER = 'a8'
OUTPUT_TXT = 'a8.txt'
OUTPUT_JSON = 'a8.json'
WITH_2FA_FOLDER = 'a8/with_2fa'
WITHOUT_2FA_FOLDER = 'a8/without_2fa'

# Buat folder output jika belum ada
os.makedirs(WITH_2FA_FOLDER, exist_ok=True)
os.makedirs(WITHOUT_2FA_FOLDER, exist_ok=True)

# Setup logging
logging.basicConfig(
    filename='session_check.log',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)

def get_file_paths(session_name):
    return [os.path.join(SESSION_FOLDER, f) for f in os.listdir(SESSION_FOLDER)
            if f.startswith(session_name) and os.path.isfile(os.path.join(SESSION_FOLDER, f))]

def backdate_file_mod_time(paths, days=1):
    for path in paths:
        try:
            stat = os.stat(path)
            new_time = stat.st_mtime - (days * 86400)
            os.utime(path, (stat.st_atime, new_time))
            logging.info(f"✔️ Backdated: {path}")
        except Exception as e:
            logging.warning(f"❌ Gagal backdate {path}: {e}")

def move_session_files(session_name, destination_folder):
    paths = get_file_paths(session_name)
    for path in paths:
        try:
            shutil.move(path, os.path.join(destination_folder, os.path.basename(path)))
            logging.info(f"📁 Moved {path} -> {destination_folder}")
        except Exception as e:
            logging.error(f"❌ Gagal memindahkan {path}: {e}")

def delete_session_files(session_name):
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
    session_path = os.path.join(SESSION_FOLDER, session_name)
    client = TelegramClient(session_path, api_id, api_hash)

    try:
        client.connect()

        if not client.is_user_authorized():
            return "inactive", None

        # Akun aktif, login
        client.start()

        me = client.get_me()
        if me and me.phone:
            phone = f"+{me.phone}"
            active_numbers.append(phone)
            logging.info(f"📱 Active: {phone}")

        # Cek apakah pakai 2FA
        try:
            pw = client(GetPasswordRequest())
            if pw.has_password:
                logging.info(f"🔐 {session_name} menggunakan 2FA")
                return "active", "with_2fa"
            else:
                logging.info(f"🔓 {session_name} tidak menggunakan 2FA")
                return "active", "without_2fa"
        except Exception as e:
            logging.warning(f"⚠️ Gagal cek 2FA {session_name}: diasumsikan TIDAK 2FA - {e}")
            return "active", "without_2fa"

    except (AuthKeyUnregisteredError, PhoneNumberBannedError) as e:
        logging.warning(f"🚫 Session {session_name} error fatal: {e}")
        return "corrupt", None
    except FloodWaitError as e:
        logging.error(f"⚠️ FloodWaitError: Tunggu {e.seconds} detik")
        time.sleep(e.seconds + 5)
        return "retry", None
    except RPCError as e:
        logging.warning(f"⚠️ RPCError lain: {e}")
        return "corrupt", None
    except Exception as e:
        logging.error(f"❌ Error saat cek session {session_name}: {e}")
        return "corrupt", None
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
        status, session_type = check_session_status(session_name, active_numbers)
        print(f"[{idx}/{len(sessions)}] Session '{session_name}': {status.upper()}")

        if status == "active":
            total_active += 1
            backdate_file_mod_time(paths, days=1)
            if session_type == "with_2fa":
                move_session_files(session_name, WITH_2FA_FOLDER)
            else:
                move_session_files(session_name, WITHOUT_2FA_FOLDER)
        elif status == "retry":
            print("⏳ Delay sementara karena FloodWait...")
            continue
        else:
            if delete_session_files(session_name):
                total_deleted += 1

        time.sleep(1.0)

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
