import asyncio
import os
from telethon import TelegramClient
from telethon.tl.functions.auth import ResetAuthorizationsRequest

API_ID = 23416622  # ganti dengan API_ID kamu
API_HASH = 'd1bc12a03ea26416b38b4616a36112b0'  # ganti dengan API_HASH kamu

# Folder tempat sesi-sesi disimpan
SESSION_FOLDER = os.path.join(os.path.dirname(__file__), 'cek')

async def monitor_sessions():
    session_files = [f for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]
    
    # Periksa setiap sesi
    for session_file in session_files:
        session_path = os.path.join(SESSION_FOLDER, session_file)
        phone_number = session_file.replace('.session', '')

        print(f"[~] Memeriksa sesi {phone_number}...")
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            print(f"[!] {phone_number} belum login.")
            await client.disconnect()
            continue

        me = await client.get_me()
        print(f"[+] Login terdeteksi: {me.first_name} ({me.id})")

        # Mengecek apakah perangkat yang digunakan adalah perangkat HP
        # Misalnya, kita anggap perangkat HP kamu adalah "HP_Device_Name" 
        # Kamu harus mengganti dengan nama perangkat yang sesuai
        DEVICE_NAME = "Tecno TECHNO POVA 6 Pro 5G"  # ganti dengan nama perangkat HP kamu

        devices = await client.get_devices()
        device_found = False

        for device in devices:
            if DEVICE_NAME in device.device_model:
                device_found = True
                print(f"[+] Perangkat HP ditemukan: {device.device_model} ID: {device.device_id}")
                break
        
        if device_found:
            try:
                # Logout perangkat lain yang tidak sesuai
                print(f"[~] Logout perangkat lain untuk {phone_number}...")
                await client(ResetAuthorizationsRequest())
                print(f"[✅] Semua device lama untuk {phone_number} telah di-logout.")
            except Exception as e:
                print(f"[!] Gagal reset auth untuk {phone_number}: {e}")
        else:
            print(f"[!] Perangkat HP tidak terdeteksi, logout perangkat lama untuk {phone_number}.")
            try:
                await client(ResetAuthorizationsRequest())
                print(f"[✅] Semua device lama untuk {phone_number} telah di-logout.")
            except Exception as e:
                print(f"[!] Gagal reset auth untuk {phone_number}: {e}")

        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(monitor_sessions())
