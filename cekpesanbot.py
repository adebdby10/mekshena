import requests

BOT_TOKEN = '7961891403:AAE8sydM_elnN_J8uoGLQ1urCecoCDxPHdY'
CHAT_ID = '7763955214'  # Ganti dengan chat_id kamu dari @userinfobot
pesan = "✅ Bot berhasil mengirim pesan dari Python!"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    'chat_id': CHAT_ID,
    'text': pesan
}

response = requests.post(url, data=payload)

if response.status_code == 200:
    print("Pesan berhasil dikirim ke Telegram.")
else:
    print("Gagal mengirim pesan:", response.text)
