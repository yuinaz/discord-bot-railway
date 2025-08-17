SatpamBot Consolidated Patch
============================

Berisi semua file yang ditambahkan/diubah dari rangkaian patch sebelumnya:
- Presence sticky "Online • HH:MM" (cog `presence_clock_sticky.py`)
- Log ban konsisten ke satu thread di #log-botphising (cog `banlog_thread.py`)
- Deteksi gambar phishing dengan signature pHash + autoban via dashboard (cog `anti_image_phish_signature.py`)
- Command `!whitelist` (cog `whitelist.py`)
- Dashboard:
    * Tab Phish Lab (drag-and-drop signature)
    * Security: toggle Autoban, slider threshold pHash, nama thread log ban
    * Floating “Recent Bans” widget (dashboard)
    * Editor Whitelist (realtime)

File data & config:
- data/phish_phash.json       -> daftar pHash signature
- data/phish_config.json      -> { "autoban": bool, "threshold": int, "log_thread_name": "Ban Log" }
- data/whitelist_domains.json -> whitelist domain (hasil konversi dari whitelist.txt yang Anda upload)

Cara pakai patch:
1) Unzip ke root proyek SatpamBot (overwrite file yang sama).
2) Pastikan dependency terpasang: pip install -r requirements.txt
3) Jalankan aplikasi seperti biasa. Semua kontrol via Dashboard (tanpa ENV baru).

Catatan:
- Jika channel #log-botphising belum ada, buat dulu dan beri bot izin Create Public Threads.
- Whitelist editor berada di halaman Security. Perubahan berlaku realtime.
- Phish Lab untuk mendaftarkan signature gambar phishing (drag & drop).