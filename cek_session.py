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

# === Simpan sesi yang valid ke dalam file ===
def save_sessions(sessions):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f)

# === Fungsi untuk memeriksa dan menghapus sesi yang membutuhkan otorisasi ulang ===
async def remove_unverified_sessions():
    sessions = load_sessions()  # Ambil sesi dari file
    active_sessions = []  # Menyimpan sesi yang aktif dan valid

    for phone in sessions:
        print(f"[INFO] Memeriksa sesi untuk {phone}...")
        client = TelegramClient(phone, api_id, api_hash)

        try:
            await client.connect()  # Menghubungkan client dengan sesi yang ada
            if await client.is_user_authorized():
                print(f"[✅] Client aktif untuk {phone}")
                active_sessions.append(phone)  # Tambahkan sesi yang valid ke list
            else:
                print(f"[❌] {phone} memerlukan OTP untuk login (sesi akan dihapus)")

            await client.disconnect()  # Disconnect setelah memeriksa sesi

        except Exception as e:
            print(f"[❌] Gagal menginisialisasi client untuk {phone}: {e}")
            continue  # Lewati client ini jika gagal untuk menghindari crash

    # Hapus sesi yang tidak valid dari file sessions.json
    updated_sessions = [session for session in sessions if session in active_sessions]
    save_sessions(updated_sessions)  # Menyimpan kembali sesi yang valid ke file
    print(f"[INFO] Sesi yang tidak aktif telah dihapus. Total sesi aktif: {len(updated_sessions)}")

# === Program Utama untuk Menghapus Sesi Tidak Aktif ===
if __name__ == "__main__":
    asyncio.run(remove_unverified_sessions())  # Jalankan fungsi remove_unverified_sessions untuk memeriksa sesi
