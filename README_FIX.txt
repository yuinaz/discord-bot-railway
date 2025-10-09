==============================
SatpamLeina — Smoke Dummy Fix
==============================

Apa ini?
--------
Patch kecil buat *offline smoke test* supaya `DummyBot` punya stub:
- `wait_until_ready()` (no-op)
- `guilds` (return [])
- `get_channel()` (return None)
- `loop` (return event loop yang aman)
- `user` (namespace dummy)
- `is_closed()` dan `close()` (no-op)

HAL INI MENCEGAH error:
  AttributeError: '_DummyBot' object has no attribute 'wait_until_ready'

Cara pakai (Windows / Git Bash)
--------------------------------
1) Extract ZIP ini ke folder repo:  G:\DiscordBot\SatpamLeina
   (Pastikan file patch ada di: patches/patch_dummy_waitready.py, dst.)

2) Jalankan patcher:
     cd /g/DiscordBot/SatpamLeina
     python patches/patch_dummy_waitready.py

   Output akan kasih tahu apakah file sudah dipatch.
   Backup otomatis disimpan di: smoke_utils.py.bak-<timestamp>

3) (Opsional) Verifikasi:
     python patches/verify_dummy_waitready.py

   Harus muncul: "OK — DummyBot has wait_until_ready and safe stubs."

4) Jalankan smoke offline:
     export PYTHONPATH="$(pwd)"     # Git Bash
     # atau: set PYTHONPATH=%CD%    # CMD
     python scripts/smoke_deep.py

Catatan
-------
- Patch ini **hanya menyentuh module** (smoke_utils.py), tidak pakai ENV.
- Idempotent: aman dijalankan berulang; kalau method sudah ada, patcher tidak dobel-inject.
- Tidak login ke Discord. Ini murni offline import+setup check.

Kalau masih ada error lain setelah ini, kirim log terakhirnya ya.
