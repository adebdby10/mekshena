import os
from telethon.sync import TelegramClient
from telethon.tl.types import Channel, ChannelParticipantAdmin, ChannelParticipantCreator
from telethon.tl.functions.channels import GetParticipantRequest
import asyncio

# Konfigurasi
api_id = 23520639
api_hash = 'bcbc7a22cde8fa2ba7d1baad086086ca'
session_dir = 'a5_sessions'  # folder tempat file .session

absen_sessions = []

async def check_admin_groups(session_file):
    session_name = os.path.splitext(session_file)[0]
    session_path = os.path.join(session_dir, session_name)
    client = TelegramClient(session_path, api_id, api_hash)

    try:
        print(f"\n🔍 Memeriksa session: {session_name}")
        await client.connect()

        if not await client.is_user_authorized():
            print(f"⚠️  Session {session_name} belum login. Melewati...")
            absen_sessions.append(f"{session_name} (Belum login)")
            return

        me = await client.get_me()
        print(f"✔️  Logged in sebagai: {me.phone}")

        dialogs = await client.get_dialogs()
        admin_groups = []

        for dialog in dialogs:
            entity = dialog.entity
            if isinstance(entity, Channel) and entity.megagroup:
                try:
                    participant = await client(GetParticipantRequest(
                        channel=entity,
                        user_id=me.id
                    ))
                    if isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
                        print(f"✅ Admin di grup: {entity.title}")
                        admin_groups.append(entity.title)
                except Exception:
                    pass

        with open("admin_groups_by_session.txt", "a", encoding="utf-8") as f:
            f.write(f"\nSession: {session_name} ({me.phone})\n")
            if admin_groups:
                for group in admin_groups:
                    f.write(f" - {group}\n")
            else:
                f.write(" (tidak jadi admin di grup manapun)\n")
                absen_sessions.append(f"{session_name} ({me.phone})")

    except Exception as e:
        print(f"❌ Gagal memproses session {session_name}: {e}")
        absen_sessions.append(f"{session_name} (ERROR)")
    finally:
        await client.disconnect()

async def main():
    session_files = [f for f in os.listdir(session_dir) if f.endswith('.session')]
    for session_file in session_files:
        await check_admin_groups(session_file)

    print("\n📍 Session yang TIDAK menjadi admin di grup manapun atau gagal login:")
    if absen_sessions:
        for s in absen_sessions:
            print(f" - {s}")
    else:
        print("Semua session adalah admin di minimal 1 grup.")

asyncio.run(main())
