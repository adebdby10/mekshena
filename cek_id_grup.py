from telethon.sync import TelegramClient
from telethon.tl.types import Channel, Chat

# Ganti dengan API milikmu
API_ID = 29564591
API_HASH = '99d943dcb43f77dd61c9b020105a541b'

# Nama file .session akunmu
SESSION_NAME = '+6289613704630'  # tanpa .session

with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
    dialogs = client.get_dialogs()

    print("📋 Daftar Grup dan ID-nya:")
    for dialog in dialogs:
        entity = dialog.entity
        if isinstance(entity, (Channel, Chat)):
            if getattr(entity, 'megagroup', False):  # Hanya group, bukan channel biasa
                print(f"- {entity.title} | ID: {entity.id}")
