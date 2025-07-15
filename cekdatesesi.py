import os
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.tl.functions.account import GetAuthorizationsRequest

API_ID = 23416622
API_HASH = 'd1bc12a03ea26416b38b4616a36112b0'
SESSION_FOLDER = os.path.join(os.path.dirname(__file__), 'a24_sessions')

MIN_SESSION_AGE_HOURS = 12  # Batas minimum umur sesi

async def is_session_ready(session_path):
    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return None

    try:
        auths = await client(GetAuthorizationsRequest())
    except Exception as e:
        print(f"[!] Gagal akses auth info: {e}")
        await client.disconnect()
        return None

    current_device = next((a for a in auths.authorizations if a.current), None)

    if current_device:
        age = datetime.now(timezone.utc) - current_device.date_created
        await client.disconnect()
        if age >= timedelta(hours=MIN_SESSION_AGE_HOURS):
            return {
                "session": session_path,
                "created": current_device.date_created,
                "last_active": current_device.date_active,
                "device_model": current_device.device_model,
                "age_hours": round(age.total_seconds() / 3600, 2)
            }
    await client.disconnect()
    return None

async def main():
    print(f"[🔍] Mendeteksi sesi yang bisa logout semua perangkat (usia ≥ {MIN_SESSION_AGE_HOURS} jam)...\n")

    if not os.path.exists(SESSION_FOLDER):
        print("[!] Folder session tidak ditemukan.")
        return

    session_files = [f for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]
    if not session_files:
        print("[!] Tidak ada sesi ditemukan.")
        return

    ready_sessions = []

    for filename in session_files:
        session_path = os.path.join(SESSION_FOLDER, filename)
        try:
            result = await is_session_ready(session_path)
            if result:
                ready_sessions.append(result)
        except Exception as e:
            print(f"[!] Gagal proses {filename}: {e}")

    if ready_sessions:
        print(f"\n[✅] {len(ready_sessions)} sesi siap digunakan untuk logout semua perangkat:\n")
        for s in ready_sessions:
            print(f"• {s['session']}")
            print(f"  - Created     : {s['created']}")
            print(f"  - Last Active : {s['last_active']}")
            print(f"  - Device      : {s['device_model']}")
            print(f"  - Age         : {s['age_hours']} jam\n")
    else:
        print("[ℹ️] Belum ada sesi yang cukup umur untuk logout semua perangkat.")

if __name__ == "__main__":
    asyncio.run(main())
