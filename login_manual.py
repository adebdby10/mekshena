from telethon.sync import TelegramClient

api_id = 26763615
api_hash = '4d8aa7c999f425c489422548d1db0bd7'

with TelegramClient('main2', api_id, api_hash) as client:
    print("✅ Login berhasil.")
