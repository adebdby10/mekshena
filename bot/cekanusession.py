import os

SESSION_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cek'))

print(f"📂 Folder session: {SESSION_FOLDER}")

# Tampilkan semua file di folder session
if os.path.exists(SESSION_FOLDER):
    files = os.listdir(SESSION_FOLDER)
    if files:
        print("📄 Daftar session yang ditemukan:")
        for file in files:
            print(" -", file)
    else:
        print("⚠️ Folder kosong, tidak ada session.")
else:
    print("❌ Folder tidak ditemukan.")
