import asyncio
import os
import shutil
from telethon import TelegramClient
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest

API_ID = 23520639
API_HASH = 'bcbc7a22cde8fa2ba7d2baad086086ca'

DEVICE_NAME = "pc 64bit"

SESSION_FOLDER = os.path.join(os.path.dirname(__file__), '6/without_2fa')
SUCCESS_FOLDER = os.path.join(os.path.dirname(__file__), '6/without_2fa')

successfully_logged_out_numbers = []
total_sessions_processed = 0
original_timestamps = {}

def save_original_timestamp(file_path):
    if os.path.exists(file_path):
        stat = os.stat(file_path)
        original_timestamps[file_path] = (stat.st_atime, stat.st_mtime)

def restore_timestamp(file_path):
    if file_path in original_timestamps:
        try:
            os.utime(file_path, original_timestamps[file_path])
        except Exception as e:
            print(f"[⚠️] Gagal mengembalikan timestamp untuk {file_path}: {e}")

def move_session_file(session_path):
    if not os.path.exists(SUCCESS_FOLDER):
        os.makedirs(SUCCESS_FOLDER)

    base = os.path.basename(session_path)
    new_path = os.path.join(SUCCESS_FOLDER, base)
    shutil.move(session_path, new_path)
    restore_timestamp(new_path)

    journal_path = session_path + "-journal"
    if os.path.exists(journal_path):
        new_journal_path = os.path.join(SUCCESS_FOLDER, os.path.basename(journal_path))
        shutil.move(journal_path, new_journal_path)
        restore_timestamp(new_journal_path)

async def logout_session(session_path):
    global total_sessions_processed
    total_sessions_processed += 1

    save_original_timestamp(session_path)
    journal_path = session_path + "-journal"
    if os.path.exists(journal_path):
        save_original_timestamp(journal_path)

    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print(f"[!] Sesi belum login: {session_path}")
        await client.disconnect()
        restore_timestamp(session_path)
        if os.path.exists(journal_path):
            restore_timestamp(journal_path)
        return

    me = await client.get_me()
    phone_number = me.phone
    print(f"\n[+] Login sebagai: {me.first_name} ({me.id}) - +{phone_number} [{session_path}]")

    try:
        authorizations = await client(GetAuthorizationsRequest())
    except Exception as e:
        print(f"[!] Gagal mendapatkan daftar perangkat: {e}")
        await client.disconnect()
        restore_timestamp(session_path)
        if os.path.exists(journal_path):
            restore_timestamp(journal_path)
        return

    logged_out = False

    for device in authorizations.authorizations:
        model = device.device_model.lower()
        if not device.current:
            try:
                await client(ResetAuthorizationRequest(hash=device.hash))
                print(f"[~] Logout perangkat: {device.device_model} ({device.app_name})")
                logged_out = True
            except Exception as e:
                print(f"[⚠️] Gagal logout perangkat {device.device_model}: {e}")
        else:
            print(f"[i] Lewati perangkat saat ini: {device.device_model}")

    await client.disconnect()
    if logged_out:
        print(f"[✅] Perangkat lain berhasil di-logout untuk +{phone_number}")
        successfully_logged_out_numbers.append(f"+{phone_number}")
        move_session_file(session_path)
    else:
        print(f"[i] Tidak ada perangkat lain yang di-logout untuk +{phone_number}")
        restore_timestamp(session_path)
        if os.path.exists(journal_path):
            restore_timestamp(journal_path)

async def main():
    if not os.path.exists(SESSION_FOLDER):
        print(f"[!] Folder sesi tidak ditemukan: {SESSION_FOLDER}")
        return

    session_files = [f for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]
    if not session_files:
        print("[!] Tidak ada file session ditemukan.")
        return

    print(f"[~] Memproses {len(session_files)} session...\n")

    for session_file in session_files:
        session_path = os.path.join(SESSION_FOLDER, session_file)
        try:
            await logout_session(session_path)
        except Exception as e:
            print(f"[!] Error saat memproses {session_file}: {e}")
            restore_timestamp(session_path)
            journal_path = session_path + "-journal"
            if os.path.exists(journal_path):
                restore_timestamp(journal_path)

    print(f"\n[~] Total sesi yang diproses: {total_sessions_processed}")
    print(f"[✅] Jumlah sesi yang berhasil logout perangkat lain: {len(successfully_logged_out_numbers)}")

    if successfully_logged_out_numbers:
        print("[✅] Daftar nomor yang berhasil logout perangkat lain:")
        for number in successfully_logged_out_numbers:
            print(f" - {number}")
    else:
        print("[i] Tidak ada sesi yang berhasil logout perangkat lain.")

if __name__ == "__main__":
    asyncio.run(main())
