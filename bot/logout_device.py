from telethon.sync import TelegramClient
from telethon import functions

api_id = 23520639  # Ganti dengan API ID kamu
api_hash = "bcbc7a22cde8fa2ba7d1baad086086ca"  # Ganti dengan API HASH kamu

async def logout_other_devices(update, context, session_path):
    try:
        from os.path import exists
        if not exists(session_path):
            await update.callback_query.edit_message_text("❌ Session tidak ditemukan.")
            return

        client = TelegramClient(session_path, api_id, api_hash)
        await client.connect()

        if not await client.is_user_authorized():
            await update.callback_query.edit_message_text("❌ Session belum login.")
            await client.disconnect()
            return

        await client(functions.auth.ResetAuthorizationsRequest())
        await update.callback_query.edit_message_text("✅ Perangkat lain berhasil logout.")
        await client.disconnect()

    except Exception as e:
        await update.callback_query.edit_message_text(f"❌ Gagal logout perangkat lain.\n{str(e)}")
