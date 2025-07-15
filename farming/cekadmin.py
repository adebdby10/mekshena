import os
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import Channel, Chat
from telethon.tl.functions.channels import GetParticipantRequest

# --- KONFIGURASI ---
API_ID = 29564591  # Ganti dengan API ID Anda
API_HASH = '99d943dcb43f77dd61c9b020105a541b'  # Ganti dengan API Hash Anda
SESSION_DIR = 'a4'  # Folder tempat file .session berada

def is_admin(client, entity):
    try:
        if isinstance(entity, Channel):
            result = client(GetParticipantRequest(entity, 'me'))
            participant = result.participant
            return getattr(participant, 'admin_rights', None) is not None
        elif isinstance(entity, Chat):
            me = client.get_me()
            participants = client.get_participants(entity)
            for p in participants:
                if p.id == me.id and getattr(p.participant, 'admin_rights', None):
                    return True
    except Exception as e:
        print(f"  [!] Error saat cek admin: {e}")
    return False

def check_session(session_file):
    session_name = session_file.replace('.session', '')
    print(f"\n🔍 Memeriksa session: {session_name}")
    try:
        client = TelegramClient(os.path.join(SESSION_DIR, session_name), API_ID, API_HASH)
        client.connect()
        if not client.is_user_authorized():
            print("  [!] Session belum login atau expired.")
            client.disconnect()
            return

        me = client.get_me()
        print(f"  👤 Login sebagai: {me.username or me.phone}")

        dialogs = client.get_dialogs()
        for dialog in dialogs:
            entity = dialog.entity
            if isinstance(entity, (Channel, Chat)):
                admin_status = is_admin(client, entity)
                print(f"  - {entity.title}: {'✅ Admin' if admin_status else '❌ Bukan admin'}")

        client.disconnect()

    except SessionPasswordNeededError:
        print("  [!] Butuh verifikasi 2FA. Lewati.")
    except FloodWaitError as e:
        print(f"  [!] Terkena FloodWait. Tunggu {e.seconds} detik.")
    except Exception as e:
        print(f"  [!] Error lain: {e}")

# --- MULAI ---
if __name__ == "__main__":
    if not os.path.isdir(SESSION_DIR):
        print(f"Folder {SESSION_DIR} tidak ditemukan.")
        exit()

    session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not session_files:
        print("Tidak ada file session ditemukan.")
        exit()

    for session_file in session_files:
        check_session(session_file)
