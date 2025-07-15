import os
import asyncio
from telethon import TelegramClient
from telethon.tl.functions.account import GetAuthorizationsRequest, ResetAuthorizationRequest

API_ID = 23416622
API_HASH = 'd1bc12a03ea26416b38b4616a36112b0'
SESSION_FOLDER = os.path.join(os.path.dirname(__file__), 'a24_sessions')

async def force_logout_other_devices(session_path):
    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print(f"[✘] Tidak login: {session_path}")
        await client.disconnect()
        return

    try:
        auths = await client(GetAuthorizationsRequest())
        me = await client.get_me()
        current_device = next((a for a in auths.authorizations if a.current), None)

        if not current_device:
            print(f"[✘] Tidak bisa identifikasi device saat ini: {session_path}")
            await client.disconnect()
            return

        print(f"[🔐] Mempertahankan: {current_device.device_model} ({current_device.platform})")
        logout_count = 0

        for auth in auths.authorizations:
            if not auth.current:
                try:
                    await client(ResetAuthorizationRequest(hash=auth.hash))
                    print(f"    - ✅ Logout: {auth.device_model} ({auth.platform})")
                    logout_count += 1
                except Exception as e:
                    print(f"    - ⚠️ Gagal logout {auth.device_model}: {e}")

        print(f"[🚪] Logout {logout_count} perangkat lain: {me.first_name} (+{me.phone})\n")
    except Exception as e:
        print(f"[!] Error saat proses {session_path}: {e}")
    finally:
        await client.disconnect()

async def main():
    print(f"[⚙️] Menjalankan logout paksa semua device lain...\n")

    if not os.path.exists(SESSION_FOLDER):
        print("[!] Folder sesi tidak ditemukan.")
        return

    session_files = [f for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]
    if not session_files:
        print("[!] Tidak ada file sesi ditemukan.")
        return

    for filename in session_files:
        session_path = os.path.join(SESSION_FOLDER, filename)
        try:
            await force_logout_other_devices(session_path)
        except Exception as e:
            print(f"[!] Error saat memproses {filename}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
