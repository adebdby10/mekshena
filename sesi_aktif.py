import json
import os
from telethon import TelegramClient
import asyncio

# === Konfigurasi ===
api_id = '23416622'  # Ganti dengan api_id Anda
api_hash = 'd1bc12a03ea26416b38b4616a36112b0'  # Ganti dengan api_hash Anda
SESSIONS_FILE = "sessions.json"

# === Muat sesi yang sudah login ===
def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r") as f:
            return json.load(f)
    return []

# === Fungsi untuk menghitung sesi yang masih aktif ===
async def count_active_sessions():
    sessions = load_sessions()  # Ambil sesi dari file
    active_sessions = 0  # Menyimpan jumlah sesi yang aktif

    for phone in sessions:
        print(f"[INFO] Memeriksa sesi untuk {phone}...")
        client = TelegramClient(phone, api_id, api_hash)

        try:
            await client.connect()  # Menghubungkan client dengan sesi yang ada
            if await client.is_user_authorized():
                active_sessions += 1  # Jika sesi aktif, tambahkan ke hitungan
                print(f"[✅] Client aktif untuk {phone}")
            else:
                print(f"[❌] {phone} memerlukan OTP untuk login (sesi tidak aktif)")

            await client.disconnect()  # Disconnect setelah memeriksa sesi

        except Exception as e:
            print(f"[❌] Gagal menginisialisasi client untuk {phone}: {e}")
            continue  # Lewati client ini jika gagal untuk menghindari crash

    print(f"[INFO] Total sesi aktif: {active_sessions}")  # Menampilkan total sesi yang aktif

# === Program Utama untuk Menghitung Total Sesi Aktif ===
if __name__ == "__main__":
    asyncio.run(count_active_sessions())  # Jalankan fungsi count_active_sessions untuk menghitung sesi aktif
