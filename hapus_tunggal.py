import os
import asyncio
from telethon import TelegramClient

API_ID = 26763615  # Ganti dengan API ID kamu
API_HASH = '4d8aa7c999f425c489422548d1db0bd7'  # Ganti dengan API HASH kamu

# Ganti ini dengan nama file session tanpa .session
SESSION_NAME = '6282219130216'

async def hapus_dari_session(session_name):
    session_file = f"{session_name}.session"

    if not os.path.exists(session_file):
        print(f"❌ File session tidak ditemukan: {session_file}")
        return

    # Pakai nama session langsung (Telethon akan otomatis cari .session di folder saat ini)
    client = TelegramClient(session_name, API_ID, API_HASH)

    try:
        await client.start()
        me = await client.get_me()
        print(f"✅ Login sebagai {me.username or me.first_name} ({me.phone})")

        dialogs = await client.get_dialogs()
        for dialog in dialogs:
            try:
                await client.delete_dialog(dialog.id)
                print(f"🗑️ Dialog '{dialog.name}' dihapus.")
            except Exception as e:
                print(f"❌ Gagal hapus dialog '{dialog.name}': {e}")

        await client.disconnect()
        print("✅ Semua pesan berhasil dihapus.")

    except Exception as e:
        print(f"❌ Terjadi error: {e}")

if __name__ == '__main__':
    asyncio.run(hapus_dari_session(SESSION_NAME))
