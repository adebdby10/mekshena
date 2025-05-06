import os
import asyncio
import random
from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.contacts import GetContactsRequest
from telethon.tl.functions.channels import (
    InviteToChannelRequest,
    GetParticipantsRequest,
    JoinChannelRequest
)
from telethon.tl.types import ChannelParticipantsSearch, InputPeerUser
from telegram import Update
from telegram.ext import ContextTypes

from config import SESSION_FOLDER, GROUP_USERNAME_OR_ID, API_ID, API_HASH

async def invite_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    session_path = os.path.join(SESSION_FOLDER, f"{phone_number}.session")
    if not os.path.exists(session_path):
        await update.callback_query.message.reply_text(f"❌ Session tidak ditemukan untuk {phone_number}")
        return

    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.start()

    if not await client.is_user_authorized():
        await update.callback_query.message.reply_text(f"⚠️ Session belum login: {phone_number}")
        await client.disconnect()
        return

    # Join ke grup terlebih dahulu
    try:
        await client(JoinChannelRequest(GROUP_USERNAME_OR_ID))
    except Exception as e:
        await update.callback_query.message.reply_text(f"❌ Gagal join ke grup: {str(e)}")
        await client.disconnect()
        return

    # Ambil daftar kontak dari akun
    contacts = await client(GetContactsRequest(hash=0))

    # Ambil daftar peserta grup
    participants = await client(GetParticipantsRequest(
        channel=GROUP_USERNAME_OR_ID,
        filter=ChannelParticipantsSearch(''),
        offset=0,
        limit=10000,
        hash=0
    ))
    existing_user_ids = set(p.id for p in participants.users)

    # Hanya undang kontak mutual yang belum ada di grup
    kontak_baru = [
        u for u in contacts.users
        if u.id not in existing_user_ids and getattr(u, 'mutual_contact', False)
    ]

    invited, failed = 0, 0
    total = len(contacts.users)

    progress = await update.callback_query.message.reply_text(
        f"⏳ Memulai invite untuk `{phone_number}`...\nKontak mutual baru: {len(kontak_baru)}",
        parse_mode='Markdown'
    )
    old_msg = progress

    for idx, user in enumerate(kontak_baru, 1):
        try:
            user_input = InputPeerUser(user.id, user.access_hash)
            await client(InviteToChannelRequest(channel=GROUP_USERNAME_OR_ID, users=[user_input]))
            invited += 1
        except FloodWaitError as e:
            print(f"⚠️ Flood wait {e.seconds}s untuk {user.id}")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            failed += 1
            print(f"❌ Gagal invite {user.id}: {str(e)}")

        if idx % 10 == 0 or idx == len(kontak_baru):
            try:
                if old_msg:
                    await old_msg.delete()
                old_msg = await update.effective_chat.send_message(
                    f"📨 Proses akun `{phone_number}`...\n"
                    f"📤 Diundang: {invited}\n❌ Gagal: {failed}\n✅ Sudah di grup: {total - len(kontak_baru)}\n"
                    f"➡️ Diproses: {idx}/{len(kontak_baru)}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"⚠️ Gagal update progress: {str(e)}")

        await asyncio.sleep(2 + random.random())

    await client.disconnect()
