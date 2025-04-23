from telethon import TelegramClient
from telethon.tl.functions.account import UpdatePasswordSettingsRequest
from telethon.tl.types import PasswordInput  # Pastikan mengimpor PasswordInput
import os

# Ganti dengan informasi Anda
api_id = '23520639'  # Ganti dengan API ID Anda
api_hash = 'bcbc7a22cde8fa2ba7d1baad086086ca'  # Ganti dengan API Hash Anda
session_name = '+6281290159173.session'  # Nama file session
password = 'adep140201'  # Password yang ingin Anda atur untuk verifikasi dua langkah

# Membuat client dengan file session yang sudah ada
client = TelegramClient(session_name, api_id, api_hash)

async def enable_two_step_verification():
    await client.start()

    # Menyiapkan pengaturan password baru dengan objek PasswordInput
    password_input = PasswordInput(
        new_password=password,  # Password baru yang akan digunakan
        hint="This is my password hint"  # Anda bisa menambahkan hint password
    )

    # Mengaktifkan verifikasi dua langkah dengan password yang ditentukan
    result = await client(UpdatePasswordSettingsRequest(
        current_password=None,  # Tidak ada password lama yang dimasukkan
        new_password=password_input  # Menggunakan PasswordInput yang telah disiapkan
    ))

    print("Two-step verification has been enabled with the new password.")

# Menjalankan client dan fungsi
with client:
    client.loop.run_until_complete(enable_two_step_verification())
