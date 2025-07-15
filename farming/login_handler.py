import os
import shutil
from telethon import TelegramClient
from telethon.errors import (
    PhoneNumberUnoccupiedError, SessionPasswordNeededError, PhoneCodeInvalidError
)
from config import SESSIONS_FOLDER, SESSIONS_FOLDER_FINAL, is_valid_phone_number
from spoof_device import apply_spoof_device

pending_login = {}

async def request_otp(phone):
    session_path = os.path.join(SESSIONS_FOLDER, phone)
    client = TelegramClient(session_path, 29564591, '99d943dcb43f77dd61c9b020105a541b')
    await apply_spoof_device(client, phone)
    await client.connect()

    if await client.is_user_authorized():
        print(f"[✅] {phone} sudah login.")
        await move_valid_session(phone)
        await client.disconnect()
        return

    sent = await client.send_code_request(phone)
    pending_login[phone] = (client, sent.phone_code_hash)
    print(f"[📨] OTP dikirim ke {phone}")

async def complete_login(phone, otp):
    if phone not in pending_login:
        print(f"[⚠️] Tidak ada request OTP untuk {phone}")
        return

    client, phone_code_hash = pending_login[phone]
    await client.connect()

    try:
        await client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)

    except PhoneNumberUnoccupiedError:
        print(f"[🆕] {phone} belum terdaftar, daftar akun baru...")
        await client.sign_up(otp, first_name="UserBaru")

    except SessionPasswordNeededError:
        print(f"[🔐] 2FA aktif di {phone}, butuh password.")
        await client.disconnect()
        return

    except PhoneCodeInvalidError:
        print(f"[❌] OTP salah untuk {phone}")
        await client.disconnect()
        return

    except Exception as e:
        print(f"[❌] Error login {phone}: {e}")
        await client.disconnect()
        return

    if await client.is_user_authorized():
        print(f"[✅] Login sukses {phone}")
        await move_valid_session(phone)

    else:
        print(f"[❌] Login gagal untuk {phone} (tidak authorized)")

    await client.disconnect()
    del pending_login[phone]

async def complete_login_with_password(phone, otp, password):
    if phone not in pending_login:
        print(f"[⚠️] Tidak ada OTP pending untuk {phone}")
        return

    client, phone_code_hash = pending_login[phone]
    await client.connect()

    try:
        await client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
    except SessionPasswordNeededError:
        try:
            await client.sign_in(password=password)
            if await client.is_user_authorized():
                print(f"[✅] Login sukses 2FA {phone}")
                await move_valid_session(phone)
        except Exception as e:
            print(f"[❌] Gagal login 2FA {phone}: {e}")
    except Exception as e:
        print(f"[❌] Gagal login {phone}: {e}")

    await client.disconnect()
    del pending_login[phone]

def get_pending():
    return pending_login

def move_valid_session(phone):
    """Pindahkan sesi yang valid ke folder final."""
    old_path = os.path.join(SESSIONS_FOLDER, phone + ".session")
    new_path = os.path.join(SESSIONS_FOLDER_FINAL, phone + ".session")
    if os.path.exists(old_path):
        os.makedirs(SESSIONS_FOLDER_FINAL, exist_ok=True)
        shutil.move(old_path, new_path)
        print(f"[📁] Session {phone} dipindah ke folder valid.")
    else:
        print(f"[⚠️] Session file untuk {phone} tidak ditemukan.")
