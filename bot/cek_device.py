from telethon.sync import TelegramClient
import os
from config import SESSION_FOLDER


# Ganti dengan API_ID dan API_HASH kamu
api_id = '23416622'
api_hash = 'd1bc12a03ea26416b38b4616a36112b0'

async def check_devices_in_sessions():
    # Mengambil file sesi yang ada
    session_files = [f for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]
    
    if not session_files:
        print("Tidak ada sesi yang ditemukan.")
        return

    for session_file in session_files:
        session_path = os.path.join(SESSION_FOLDER, session_file)

        print(f"\nMemeriksa perangkat untuk sesi: {session_file}")

        # Mulai client dengan sesi tertentu
        client = TelegramClient(session_path, api_id, api_hash)
        
        await client.start()

        # Mendapatkan informasi pengguna
        user_info = await client.get_me()

        print(f"Nama Pengguna: {user_info.username}")
        print(f"ID Pengguna: {user_info.id}")
        print(f"Nama Lengkap: {user_info.first_name} {user_info.last_name}")
        print(f"Perangkat Terhubung: {session_file}")

        await client.disconnect()

# Jalankan fungsi
if __name__ == "__main__":
    import asyncio
    asyncio.run(check_devices_in_sessions())
