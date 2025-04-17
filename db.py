import psycopg2
from psycopg2 import sql

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'adep140201',
    'database': 'telebot'
}

# Simpan data sesi login
def save_session_to_db(phone, status):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Pastikan tabel 'sessions' sudah ada, jika tidak buat tabel baru
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                phone_number TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'success',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Menyimpan atau memperbarui session berdasarkan phone_number
        cur.execute("""
            INSERT INTO sessions (phone_number, status)
            VALUES (%s, %s)
            ON CONFLICT (phone_number) 
            DO UPDATE SET status = EXCLUDED.status, created_at = CURRENT_TIMESTAMP
        """, (phone, status))

        conn.commit()
        cur.close()
        conn.close()
        print(f"[💾] Session {phone} disimpan ke DB dengan status: {status}")
    except Exception as e:
        print(f"[❌] Gagal simpan session ke DB: {e}")

# Ambil daftar sesi login
def load_sessions_from_db():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("SELECT phone_number FROM sessions WHERE status = 'success'")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [row[0] for row in rows]
    except Exception as e:
        print(f"[❌] Gagal load session dari DB: {e}")
        return []
