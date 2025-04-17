import asyncio
from telethon import TelegramClient

api_id = 26763615
api_hash = '4d8aa7c999f425c489422548d1db0bd7'

async def main():
    client = TelegramClient('main2', api_id, api_hash)
    await client.start()

    dialogs = await client.get_dialogs()
    print("🔍 Grup yang diikuti oleh akun main3:")
    for dialog in dialogs:
        if dialog.is_group:
            print(f" - {dialog.name} (ID: {dialog.id})")

    await client.disconnect()

asyncio.run(main())
