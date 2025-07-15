import os
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.account import GetAuthorizationsRequest
from datetime import datetime, timezone

API_ID = 23416622
API_HASH = 'd1bc12a03ea26416b38b4616a36112b0'
SESSION_FOLDER = os.path.join(os.path.dirname(__file__), 'a24_sessions')

async def check_devices(session_path):
    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print(f"[✘] Belum login: {session_path}")
        await client.disconnect()
        return

    try:
        me = await client.get_me()
        auths = await client(GetAuthorizationsRequest())
        print(f"\n[📱] Session: {session_path}")
        print(f"     User : {me.first_name} (+{me.phone})")
        print(f"     Total Devices: {len(auths.authorizations)}")

        for i, auth in enumerate(auths.authorizations, 1):
            created = auth.date_created.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            last_active = auth.date_active.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            current = "✅" if auth.current else " "
            print(f"  {i}. [{current}] {auth.device_model} - {auth.platform} - IP: {auth.ip}")
            print(f"      Created    : {created}")
            print(f"      Last Active: {last_active}")
    except Exception as e:
        print(f"[!] Gagal cek session {session_path}: {e}")
    finally:
        await client.disconnect()

async def main():
    if not os.path.exists(SESSION_FOLDER):
        print("[!] Folder session tidak ditemukan.")
        return

    session_files = [f for f in os.listdir(SESSION_FOLDER) if f.endswith(".session")]
    if not session_files:
        print("[!] Tidak ada session ditemukan.")
        return

    print(f"[🔍] Mengecek device aktif dari {len(session_files)} session...\n")
    for filename in session_files:
        session_path = os.path.join(SESSION_FOLDER, filename)
        await check_devices(session_path)

if __name__ == "__main__":
    asyncio.run(main())
