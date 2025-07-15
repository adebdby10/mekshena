import os
import shutil
import json
import random
from telethon import TelegramClient
from telethon.errors import (
    PhoneNumberUnoccupiedError,
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
)
from telethon.tl.functions.auth import SignUpRequest
from config import api_id, api_hash, SESSIONS_FOLDER, SESSIONS_FOLDER_FINAL
from spoof_device import apply_spoof_device

pending_login = {}

async def request_otp(phone):
    session_path = os.path.join(SESSIONS_FOLDER, phone)
    client = TelegramClient(session_path, api_id, api_hash)
    await apply_spoof_device(client, phone)
    await client.connect()

    if await client.is_user_authorized():
        print(f"[✅] {phone} sudah login (session aktif).")
        await client.disconnect()
        return

    try:
        sent = await client.send_code_request(phone)
    except Exception as e:
        print(f"[❌] Gagal kirim OTP ke {phone}: {e}")
        await client.disconnect()
        return

    pending_login[phone] = (client, sent.phone_code_hash)
    print(f"[📨] OTP dikirim ke {phone}")

async def complete_login(phone, otp, log_callback=None):
    if phone not in pending_login:
        print(f"[⚠️] Tidak ada request OTP untuk {phone}")
        return

    client, phone_code_hash = pending_login[phone]
    await client.connect()

    try:
        await client.sign_in(phone=phone, code=otp, phone_code_hash=phone_code_hash)
        print(f"[✅] Login sukses {phone}")
    except PhoneNumberUnoccupiedError:
        # Belum terdaftar, daftar akun baru
        first_name = f"User{random.randint(1000,9999)}"
        try:
            await client.sign_up(code=otp, phone_code_hash=phone_code_hash, first_name=first_name)
            print(f"[🆕] Akun baru berhasil dibuat untuk {phone} dengan nama {first_name}")
        except Exception as e:
            print(f"[❌] Gagal daftar akun baru {phone}: {e}")
            await client.disconnect()
            del pending_login[phone]
            return
    except SessionPasswordNeededError:
        print(f"[🔒] 2FA aktif di {phone}, mohon input password 2FA.")
        await client.disconnect()
        return
    except PhoneCodeInvalidError:
        print(f"[❌] OTP salah untuk {phone}")
        await client.disconnect()
        del pending_login[phone]
        return
    except Exception as e:
        print(f"[❌] Error login {phone}: {e}")
        await client.disconnect()
        del pending_login[phone]
        return

    # Cek otorisasi
    is_auth = await client.is_user_authorized()
    if is_auth:
        # Pindahkan session ke final
        await client.disconnect()
        await _move_session(phone)
        print(f"[📂] Session {phone} dipindahkan ke folder {SESSIONS_FOLDER_FINAL}")
        if log_callback:
            log_callback(phone)
    else:
        print(f"[❌] Session {phone} tidak valid setelah login/daftar.")

    await client.disconnect()
    if phone in pending_login:
        del pending_login[phone]

async def complete_login_with_password(phone, otp, password, log_callback=None):
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
            print(f"[✅] Login sukses 2FA {phone}")
        except Exception as e:
            print(f"[❌] Gagal login 2FA {phone}: {e}")
            await client.disconnect()
            del pending_login[phone]
            return
    except Exception as e:
        print(f"[❌] Gagal login {phone}: {e}")
        await client.disconnect()
        del pending_login[phone]
        return

    is_auth = await client.is_user_authorized()
    if is_auth:
        await client.disconnect()
        await _move_session(phone)
        print(f"[📂] Session {phone} dipindahkan ke folder {SESSIONS_FOLDER_FINAL} setelah 2FA")
        if log_callback:
            log_callback(phone)
    else:
        print(f"[❌] Session {phone} tidak valid setelah login 2FA")

    await client.disconnect()
    if phone in pending_login:
        del pending_login[phone]

def get_pending():
    return pending_login

async def _move_session(phone):
    src = os.path.join(SESSIONS_FOLDER, phone)
    dst = os.path.join(SESSIONS_FOLDER_FINAL, phone)
    if os.path.exists(src):
        if os.path.exists(dst):
            # Hapus session lama di tujuan jika ada
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
        shutil.move(src, dst)
