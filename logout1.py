import asyncio
import os
from telethon import TelegramClient
from telethon.tl.functions.account import GetAuthorizationsRequest
from telethon.tl.functions.auth import ResetAuthorizationsRequest

API_ID = 23416622
API_HASH = 'd1bc12a03ea26416b38b4616a36112b0'

# Nama perangkat HP kamu (gunakan lowercase)
DEVICE_NAME = "tecno pova 6 pro 5g"

SESSION_FOLDER = os.path.join(os.path.dirname(__file__), 'cek')

async def logout_session(session_path):
    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print(f"[!] Sesi belum login: {session_path}")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"\n[+] Login sebagai: {me.first_name} ({me.id}) [{session_path}]")

    try:
        authorizations = await client(GetAuthorizationsRequest())
    except Exception as e:
        print(f"[!] Gagal mendapatkan daftar perangkat: {e}")
        await client.disconnect()
        return

    device_found = False
    for device in authorizations.authorizations:
        model = device.device_model.lower()
        print(f"   • Perangkat: {model}")
        if DEVICE_NAME in model:
            device_found = True
            print(f"[+] Perangkat HP ditemukan: {model}")
            break

    if not device_found:
        print(f"[!] Perangkat tidak ditemukan, logout semua perangkat...")
    else:
        print(f"[~] Logout perangkat lain yang tidak sesuai...")

    try:
        await client(ResetAuthorizationsRequest())
        print(f"[✅] Semua perangkat lain berhasil di-logout untuk sesi ini.")
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

if __name__ == "__main__":
    asyncio.run(main())
