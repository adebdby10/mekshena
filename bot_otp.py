import asyncio
import re
from telethon import TelegramClient, events

# Konfigurasi API Telegram dari https://my.telegram.org
api_id = 25936778  # Ganti dengan punyamu
api_hash = 'cb2be8be4bc5742c8a409f3fed31dc8c'

# Buat client utama
client = TelegramClient('bot_session', api_id, api_hash)

# Session penyimpanan data sementara
phone_sessions = {}  # format: { '+628xxxx': {'otp': '66179'} }

# Regex untuk ambil nomor dan OTP
re_number = re.compile(r'PHONE NUMBER\s*:\s*(\+\d+)')
re_otp = re.compile(r'OTP\s*:\s*(\d{4,6})')

# ID grup target (pastikan akun sudah join grup ini)
target_chat_id = -4550563481  # Ganti dengan ID grup kamu

# Event handler semua pesan
@client.on(events.NewMessage())
async def handler(event):
    if event.chat_id != target_chat_id:
        return  # Bukan dari grup yang diinginkan

    text = event.raw_text
    number_match = re_number.search(text)
    otp_match = re_otp.search(text)

    if number_match:
        phone_number = number_match.group(1)
        if phone_number not in phone_sessions:
            phone_sessions[phone_number] = {}
            print(f"[+] Ditemukan nomor baru: {phone_number}")
        else:
            print(f"[=] Nomor sudah ada: {phone_number}")

    if otp_match and number_match:
        otp = otp_match.group(1)
        phone_number = number_match.group(1)
        phone_sessions[phone_number]['otp'] = otp
        print(f"[✓] OTP untuk {phone_number} adalah {otp}")

        # Login otomatis dengan OTP jika tersedia
        await login_with_otp(phone_number, otp)

# Fungsi login dengan OTP
async def login_with_otp(phone_number, otp_code):
    print(f"[⏳] Mencoba login ke {phone_number} dengan OTP {otp_code}")
    try:
        temp_client = TelegramClient(f'session_{phone_number}', api_id, api_hash)
        await temp_client.connect()

        if not await temp_client.is_user_authorized():
            await temp_client.send_code_request(phone_number)
            await temp_client.sign_in(phone_number, otp_code)
            print(f"[✅] Berhasil login: {phone_number}")
        else:
            print(f"[=] Sudah login: {phone_number}")
        await temp_client.disconnect()
    except Exception as e:
        print(f"[❌] Gagal login {phone_number}: {e}")

# Main bot
async def main():
    await client.start()
    print("[🚀] Bot berjalan...")

    # Debug: tampilkan daftar chat agar kamu tahu ID-nya
    print("[📋] Daftar Chat:")
    async for dialog in client.iter_dialogs():
        print(f"{dialog.name} | ID: {dialog.id}")

    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
