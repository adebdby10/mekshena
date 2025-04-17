from final2 import load_sessions  # Memastikan Anda mengimpor fungsi dari final.py

def sessions(update, context):
    sessions = load_sessions()
    if sessions:
        session_list = "\n".join(f"{i+1}. {num}" for i, num in enumerate(sessions))
        return f"✅ Daftar nomor yang sudah login:\n\n{session_list}"
    else:
        return "❌ Tidak ada nomor yang login."
