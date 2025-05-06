import os
from telethon import TelegramClient
import asyncio

# Ganti dengan nomor telepon yang ingin digunakan
phone_number = "+6285604755628"  # Nomor telepon harus dalam format internasional (misalnya, +62 untuk Indonesia)

# Ganti dengan API ID dan API Hash Anda dari https://my.telegram.org/auth
api_id = '23520639'
api_hash = 'bcbc7a22cde8fa2ba7d1baad086086ca'

# Tentukan nama file sesi
# Folder sessions akan dibuat jika belum ada
session_folder = "createsessions"
if not os.path.exists(session_folder):
    os.makedirs(session_folder)

# Nama file sesi berdasarkan nomor telepon
session_name = os.path.join(session_folder, f"session_{phone_number.replace('+', '').replace(' ', '')}.session")

# Fungsi untuk membuat file sesi
async def create_session():
    # Membuat klien Telegram
    client = TelegramClient(session_name, api_id, api_hash)
    
    # Menyambung ke server Telegram
    await client.start(phone_number)
    
    # Menampilkan informasi akun untuk memastikan berhasil login
    me = await client.get_me()
    print(f"Berhasil login sebagai {me.username} ({me.id})")

    # Menyimpan sesi ke file
    await client.disconnect()

# Jalankan fungsi untuk membuat file sesi
asyncio.run(create_session())
