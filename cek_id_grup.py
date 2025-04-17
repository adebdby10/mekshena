from telethon.sync import TelegramClient

api_id = 25936778  # ganti
api_hash = 'cb2be8be4bc5742c8a409f3fed31dc8c'

with TelegramClient('my_user_session', api_id, api_hash) as client:
    for dialog in client.iter_dialogs():
        if dialog.is_group:
            print(f'{dialog.name} - ID: {dialog.id}')
