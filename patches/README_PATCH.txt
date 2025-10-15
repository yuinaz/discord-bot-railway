Patch: DummyBot wait_until_ready (offline smoke)

Tujuan
------
Memperbaiki error saat smoke test offline:
  AttributeError: '_DummyBot' object has no attribute 'wait_until_ready'

Patch ini TIDAK mengubah konfigurasi bot saat online. Hanya menambah
fallback method async `wait_until_ready()` ke DummyBot/_DummyBot yang
dipakai oleh scripts/smoke_deep.py.

Isi
---
- patches/quick_patcher.py         → jalankan patch otomatis (idempotent)
- patches/verify_snippet.py        → opsional, verifikasi hasil patch
- patches/README_PATCH.txt         → file ini

Cara Pakai
----------
1) Extract ZIP ke ROOT project (sejajar dengan folder satpambot/).
2) Jalankan:
   python patches/quick_patcher.py
3) (opsional) Verifikasi:
   python patches/verify_snippet.py
4) Jalankan smoke test (pastikan PYTHONPATH menunjuk ke root repo):
   - Windows CMD:
       set PYTHONPATH=%cd%
       python scripts/smoke_deep.py
   - Git Bash/WSL:
       export PYTHONPATH="$(pwd)"
       python scripts/smoke_deep.py

Catatan
-------
- Patcher akan membuat backup: smoke_utils.py.bak-<timestamp>
- Patcher hanya menambahkan block patch di AKHIR file
  satpambot/bot/modules/discord_bot/helpers/smoke_utils.py
- Jika method sudah ada, patcher tidak melakukan apa-apa.

Revert
------
Kembalikan file dari backup .bak-<timestamp> secara manual bila diperlukan.
