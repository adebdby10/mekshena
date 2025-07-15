import os
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest

API_ID = 23416622
API_HASH = 'd1bc12a03ea26416b38b4616a36112b0'
SESSION_FOLDER = os.path.join(os.path.dirname(__file__), 'a23_sessions')
MIN_SESSION_AGE_HOURS = 12

async def logout_other_devices(session_path):
    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        await client.disconnect()
        return

    try:
        auths = await client(GetAuthorizationsRequest())
        me = await client.get_me()
        current_device = next((a for a in auths.authorizations if a.current), None)

        if not current_device:
            print(f"[✘] Tidak ada device saat ini ditemukan untuk: {session_path}")
            await client.disconnect()
            return

        age = datetime.now(timezone.utc) - current_device.date_created
        if age < timedelta(hours=MIN_SESSION_AGE_HOURS):
            print(f"[⏳] Sesi terlalu muda untuk logout lainnya: {me.first_name} (+{me.phone}) - {round(age.total_seconds()/3600, 2)} jam")
            await client.disconnect()
            return

        print(f"[✅] Mempertahankan device: {current_device.device_model} ({current_device.platform})")
        logout_count = 0

        for auth in auths.authorizations:
            if not auth.current:
                try:
                    await client(ResetAuthorizationRequest(hash=auth.hash))
                    logout_count += 1
                except Exception as e:
                    print(f"[!] Gagal logout device {auth.device_model}: {e}")

        print(f"[🚪] Logout {logout_count} device lain berhasil: {me.first_name} (+{me.phone})")
    except Exception as e:
        print(f"[!] Gagal proses {session_path}: {e}")
    finally:
        await client.disconnect()

async def main():
    print(f"[🔍] Mengecek sesi yang siap logout device lain (usia ≥ {MIN_SESSION_AGE_HOURS} jam)...\n")

    session_files = [f for f in os.listdir(SESSION_FOLDER) if f.endswith(".session")]
    for filename in session_files:
        session_path = os.path.join(SESSION_FOLDER, filename)
        try:
            await logout_other_devices(session_path)
        except Exception as e:
            print(f"[!] Error saat memproses {filename}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
