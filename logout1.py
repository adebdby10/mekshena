import asyncio
import os
import shutil
from telethon import TelegramClient
from telethon.tl.functions.account import GetAuthorizationsRequest
from telethon.tl.functions.auth import ResetAuthorizationsRequest

API_ID = 23416622
API_HASH = 'd1bc12a03ea26416b38b4616a36112b0'

# Nama perangkat HP kamu (gunakan lowercase)
DEVICE_NAME = "pc 64bit"

SESSION_FOLDER = os.path.join(os.path.dirname(__file__), 'a2_sessions/active')
SUCCESS_FOLDER = os.path.join(os.path.dirname(__file__), 'terminate3')

# List global untuk menyimpan nomor yang berhasil logout perangkat lain
successfully_logged_out_numbers = []
total_sessions_processed = 0

def move_session_file(session_path):
    """Pindahkan session file ke folder berhasil_logout"""
    if not os.path.exists(SUCCESS_FOLDER):
        os.makedirs(SUCCESS_FOLDER)

    base = os.path.basename(session_path)
    new_path = os.path.join(SUCCESS_FOLDER, base)

    # Pindahkan .session
    shutil.move(session_path, new_path)

    # Jika ada file tambahan seperti .session-journal, ikut dipindahkan
    journal_path = session_path + "-journal"
    if os.path.exists(journal_path):
        shutil.move(journal_path, os.path.join(SUCCESS_FOLDER, os.path.basename(journal_path)))

async def logout_session(session_path):
    global total_sessions_processed
    total_sessions_processed += 1

    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print(f"[!] Sesi belum login: {session_path}")
        await client.disconnect()
        return

    me = await client.get_me()
    phone_number = me.phone
    print(f"\n[+] Login sebagai: {me.first_name} ({me.id}) - +{phone_number} [{session_path}]")

    try:
        authorizations = await client(GetAuthorizationsRequest())
    except Exception as e:
        print(f"[!] Gagal mendapatkan daftar perangkat: {e}")
        await client.disconnect()
        return

    device_found = False
    logged_out_devices = []

    for device in authorizations.authorizations:
        model = device.device_model.lower()
        if not device.current:
            logged_out_devices.append(model)
        if DEVICE_NAME in model:
            device_found = True

    try:
        await client(ResetAuthorizationsRequest())
        print(f"[✅] Semua perangkat lain berhasil di-logout untuk sesi +{phone_number}")

        if logged_out_devices:
            print(f"   [~] Perangkat yang di-logout:")
            for model in logged_out_devices:
                print(f"   - {model}")
            successfully_logged_out_numbers.append(f"+{phone_number}")
            move_session_file(session_path)
        else:
            print(f"   [i] Tidak ada perangkat lain yang ditemukan untuk di-logout.")

    except Exception as e:
        print(f"[!] Gagal reset authorizations: {e}")

    await client.disconnect()

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
