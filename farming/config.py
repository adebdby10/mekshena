import os
import re

api_id = 29564591
api_hash = '99d943dcb43f77dd61c9b020105a541b'

SESSIONS_FOLDER = "a9"
SESSIONS_FOLDER_FINAL = "sessions1"
ALLOWED_PREFIXES = ["+62", "+60", "+971"]

os.makedirs(SESSIONS_FOLDER, exist_ok=True)
os.makedirs(SESSIONS_FOLDER_FINAL, exist_ok=True)

def is_valid_phone_number(phone_number):
    """
    Memeriksa apakah nomor telepon diawali dengan salah satu prefix yang diizinkan
    dan memiliki panjang yang sesuai.
    """
    if not isinstance(phone_number, str):
        return False
    
    # Menghapus spasi dan tanda kurung jika ada, tapi pastikan dimulai dengan '+'
    phone_number = phone_number.strip().replace(" ", "").replace("(", "").replace(")", "")
    
    if not phone_number.startswith("+"):
        return False

    for prefix in ALLOWED_PREFIXES:
        if phone_number.startswith(prefix):
            # Asumsi: Nomor valid jika diawali prefix yang diizinkan dan memiliki panjang tertentu
            # Anda bisa menyesuaikan panjang minimum/maksimum yang lebih spesifik per prefix
            return len(phone_number) >= len(prefix) + 7 and len(phone_number) <= len(prefix) + 15
    return False

# Tambahkan profil perangkat default berdasarkan phone code
DEFAULT_DEVICE_PROFILES = {
    "+62": { # Indonesia
        "device_model": "Samsung Galaxy S23",
        "system_version": "Android 13",
        "app_version": "10.10.0 (4663)",
        "lang_code": "id",
        "system_lang_code": "id-ID"
    },
    "+60": { # Malaysia
        "device_model": "Xiaomi Redmi Note 12",
        "system_version": "Android 12",
        "app_version": "10.9.0 (4620)",
        "lang_code": "ms",
        "system_lang_code": "ms-MY"
    },
    "+971": { # Uni Emirat Arab (Mungkin iPhone lebih umum)
        "device_model": "iPhone 14 Pro",
        "system_version": "iOS 17.4",
        "app_version": "10.10.0 (27306)",
        "lang_code": "en",
        "system_lang_code": "en-AE"
    },
    # Default fallback jika phone code tidak ada di atas
    "default": { 
        "device_model": "Generic Android Phone",
        "system_version": "Android 11",
        "app_version": "10.0.0 (4000)",
        "lang_code": "en",
        "system_lang_code": "en"
    }
}