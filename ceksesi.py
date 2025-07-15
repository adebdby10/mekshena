import os
import gc
import json
import shutil
import logging
import asyncio
from more_itertools import chunked
from telethon import TelegramClient
from telethon.errors import (
    AuthKeyUnregisteredError,
    PhoneNumberBannedError,
    FloodWaitError,
    RPCError,
)
from telethon.tl.functions.account import GetPasswordRequest

# Konfigurasi
api_id = 23520639
api_hash = 'bcbc7a22cde8fa2ba7d2baad086086ca'
SESSION_FOLDER = 'a43_sessions'
OUTPUT_TXT = 'a42_sessions.txt'
OUTPUT_JSON = 'a42_sessions.json'
WITH_2FA_FOLDER = os.path.join(SESSION_FOLDER, 'with_2fa')
WITHOUT_2FA_FOLDER = os.path.join(SESSION_FOLDER, 'without_2fa')
PARALLEL_LIMIT = 5
BATCH_SIZE = 100
SESSION_TIMEOUT = 30

# Setup folder & log
os.makedirs(WITH_2FA_FOLDER, exist_ok=True)
os.makedirs(WITHOUT_2FA_FOLDER, exist_ok=True)
logging.basicConfig(filename='session_check.log', level=logging.INFO,
                    format='[%(asctime)s] %(levelname)s - %(message)s')


def is_valid_session_file(f):
    return f.endswith('.session') and '+' in f


def get_file_paths(session_name):
    return [os.path.join(SESSION_FOLDER, f)
            for f in os.listdir(SESSION_FOLDER)
            if f.startswith(session_name) and os.path.isfile(os.path.join(SESSION_FOLDER, f))]


def backdate_file_mod_time(paths, days=2):
    for path in paths:
        try:
            stat = os.stat(path)
            new_time = stat.st_mtime - (days * 86400)
            os.utime(path, (stat.st_atime, new_time))
        except Exception as e:
            logging.warning(f"[BACKDATE] Gagal {path}: {e}")


def move_session_files(session_name, destination_folder):
    paths = get_file_paths(session_name)
    for path in paths:
        try:
            shutil.move(path, os.path.join(destination_folder, os.path.basename(path)))
        except Exception as e:
            logging.error(f"[MOVE] Gagal pindah {path}: {e}")


async def check_session(session_name, sema):
    session_path = os.path.join(SESSION_FOLDER, session_name)
    result = {
        "session_name": session_name,
        "status": "error",
        "session_type": None,
        "phone": None,
        "paths": get_file_paths(session_name)
    }

    async with sema:
        client = TelegramClient(session_path, api_id, api_hash)
        try:
            await client.connect()

            if not await client.is_user_authorized():
                result["status"] = "unauthorized"
                return result

            me = await client.get_me()
            result["phone"] = f"+{me.phone}" if me and me.phone else None
            result["status"] = "active"

            try:
                pw = await client(GetPasswordRequest())
                result["session_type"] = "with_2fa" if pw.has_password else "without_2fa"
            except RPCError:
                result["session_type"] = "without_2fa"

        except (AuthKeyUnregisteredError, PhoneNumberBannedError):
            result["status"] = "corrupt"
        except FloodWaitError as e:
            result["status"] = f"flood_wait_{e.seconds}"
            logging.warning(f"[FLOOD] Delay {e.seconds}s untuk {session_name}")
        except Exception as e:
            logging.error(f"[ERROR] {session_name}: {e}")
        finally:
            await client.disconnect()  # ✅ Disconnect dengan aman
        return result

def save_without_2fa_numbers(results):
    try:
        without_2fa_numbers = [
            res["phone"] for res in results
            if isinstance(res, dict) and res["status"] == "active" and res["session_type"] == "without_2fa" and res["phone"]
        ]
        with open(OUTPUT_TXT, 'w') as txt_file:
            txt_file.writelines(num + '\n' for num in without_2fa_numbers)
        with open(OUTPUT_JSON, 'w') as json_file:
            json.dump(without_2fa_numbers, json_file, indent=2)
    except Exception as e:
        logging.error(f"[SAVE] Gagal simpan: {e}")


async def main():
    with os.scandir(SESSION_FOLDER) as it:
        sessions = {
            entry.name.replace('.session', '')
            for entry in it if entry.is_file() and is_valid_session_file(entry.name)
        }

    print(f"🚀 Memulai pengea38_sessionsan {len(sessions)} sesi...\n")
    total_active = 0
    sema = asyncio.Semaphore(PARALLEL_LIMIT)
    all_results = []

    for chunk in chunked(sessions, BATCH_SIZE):
        print(f"⚙️ Memproses batch {len(chunk)} sesi...")
        tasks = [check_session(name, sema) for name in chunk]
        
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                all_results.append(result)
            except Exception as e:
                logging.error(f"[TASK ERROR] {e}")
                all_results.append(e)

    for i, result in enumerate(all_results, start=1):
        if isinstance(result, Exception):
            print(f"[{i}] ❌ Exception: {result}")
            continue

        name = result["session_name"]
        status = result["status"]
        session_type = result["session_type"]
        phone = result["phone"]
        paths = result["paths"]

        print(f"[{i}/{len(all_results)}] {name}: {status.upper()}")

        if status == "active":
            total_active += 1
            backdate_file_mod_time(paths, days=2)
            folder = WITH_2FA_FOLDER if session_type == "with_2fa" else WITHOUT_2FA_FOLDER
            move_session_files(name, folder)

        elif status == "corrupt":
            logging.warning(f"[CORRUPT] {name} dianggap rusak.")
        elif "flood_wait" in str(status):
            logging.warning(f"[FLOOD-SKIP] {name} terkena floodwait.")
        elif status == "unauthorized":
            logging.info(f"[UNAUTHORIZED] {name} tidak login.")
        else:
            logging.warning(f"[SKIP] {name} status tidak dikenali: {status}")

    save_without_2fa_numbers(all_results)

    print("\n========== SUMMARY ==========")
    print(f"✅ Total Active Sessions  : {total_active}")
    print(f"📁 File Without 2FA       : {OUTPUT_TXT}, {OUTPUT_JSON}")
    print("================================")

    # ✅ Garbage Collection setelah semua selesai
    gc.collect()


if __name__ == "__main__":
    asyncio.run(main())
