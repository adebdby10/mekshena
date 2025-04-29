from telethon.sync import TelegramClient

api_id = 29564591  # ganti
api_hash = '99d943dcb43f77dd61c9b020105a541b'

with TelegramClient('main2.session', api_id, api_hash) as client:
    for dialog in client.iter_dialogs():
        if dialog.is_group:
            print(f'{dialog.name} - ID: {dialog.id}')
