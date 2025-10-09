PATCH: DummyBot.wait_until_ready untuk Smoke Test Offline

Apa ini?
- Patch kecil agar DummyBot (di smoke_utils.py) punya method async `wait_until_ready()`.
- Menghilangkan error AttributeError: '_DummyBot' object has no attribute 'wait_until_ready' saat menjalankan scripts/smoke_deep.py.
- Idempotent & tidak mengubah konfigurasi.

Isi:
- patches/patch_dummy_waitready.py  -> patcher utama
- quick_patcher.py                  -> helper untuk menjalankan semua patch sekaligus
- verify_snippet.py                 -> verifikasi patch (opsional)

Cara pakai (Windows bash/cmd/PowerShell):
1) Ekstrak ZIP ini ke root repo (sejajar dengan folder `satpambot/`).
2) Jalankan:
   python quick_patcher.py
3) (Opsional) Verifikasi:
   python verify_snippet.py
4) Set PYTHONPATH ke root repo, lalu jalankan smoke:
   - cmd:    set PYTHONPATH=%cd%
   - bash:   export PYTHONPATH="$(pwd)"
   - lalu:   python scripts/smoke_deep.py

Catatan:
- Script patch ini hanya menyisipkan method di akhir class DummyBot jika belum ada.
- File original disimpan sebagai .bak di lokasi yang sama pada patch pertama kali.
