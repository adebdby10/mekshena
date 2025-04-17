import os
import datetime

SESSION_FOLDER = 'ew_sessions'

async def sesi_aktif_handler(update, context, phone_number):
    session_file = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    if not os.path.exists(session_file):
        await update.callback_query.message.reply_text("❌ Session tidak ditemukan.")
        return

    last_modified = os.path.getmtime(session_file)
    waktu = datetime.datetime.fromtimestamp(last_modified).strftime('%d-%m-%Y %H:%M:%S')
    await update.callback_query.message.reply_text(f"📅 Sesi aktif terakhir:\n🕒 {waktu}")
