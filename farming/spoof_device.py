from telethon.tl.functions.account import GetAuthorizationsRequest

async def apply_spoof_device(client, phone, fallback_model="Pixel 5"):
    try:
        await client.connect()
        if hasattr(client, "_init_connection"):
            auths = await client(GetAuthorizationsRequest())
            if auths.authorizations:
                last = auths.authorizations[0]
                client._init_connection.device_model = last.device_model
                client._init_connection.system_version = last.platform
                print(f"[🛠️] Spoof: {last.device_model} ({last.platform})")
            else:
                raise Exception("No previous session")
        else:
            raise Exception("_init_connection not available")
    except Exception as e:
        if not client.is_connected():
            await client.connect()
        if hasattr(client, "_init_connection"):
            client._init_connection.device_model = fallback_model
            client._init_connection.system_version = "Android 11"
        print(f"[🛠️] Spoof default: {fallback_model} ({e})")

    # Tambahan info lain
    if hasattr(client, "_init_connection"):
        conn = client._init_connection
        conn.app_version = "Telegram Android 10.0.0"
        conn.system_lang_code = "en"
        conn.lang_code = "en"
        conn.lang_pack = ""

        if phone.startswith("+62"):
            conn.country = "ID"
            conn.latitude = -6.2
            conn.longitude = 106.8167
        elif phone.startswith("+60"):
            conn.country = "MY"
            conn.latitude = 3.1390
            conn.longitude = 101.6869
        elif phone.startswith("+971"):
            conn.country = "AE"
            conn.latitude = 25.2048
            conn.longitude = 55.2708
        else:
            conn.country = "US"
            conn.latitude = 37.7749
            conn.longitude = -122.4194
