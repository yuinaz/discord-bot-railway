Patch: satpambot smoke retrofit
================================

Tujuan
------
Menghilangkan error saat `scripts/smoke_deep.py` jalan yang bunyinya:
  - "_DummyBot object has no attribute 'wait_until_ready'"
  - lalu beruntun "get_all_channels/get_channel/fetch_user" dll.

Tanpa mengubah config/format bot — hanya menambah shim no-op untuk mode smoke.

Isi patch
---------
1) **patches/retrofit_patcher.py**
   - Menambahkan fungsi `retrofit(bot)` ke:
     - `satpambot/bot/modules/discord_bot/helpers/smoke_utils.py`
     - `scripts/smoke_utils.py` (jika ada)
   - Memperbaiki `scripts/smoke_deep.py` agar:
     - Import prefer: `from satpambot.bot.modules.discord_bot.helpers import smoke_utils as smoke_utils`
       lalu fallback ke `import smoke_utils`.
     - Memanggil `smoke_utils.retrofit(bot)` setelah pembuatan `DummyBot()`.
   - Seluruh perubahan idempotent dan membuat file backup `.bak-<epoch>`.

2) **patches/verify_retrofit.py**
   - Verifikasi bahwa retrofit() sudah ada dan `smoke_deep.py` sudah dipanggilkan retrofit().

Cara pakai
----------
1. Ekstrak ZIP ini ke root project Anda (sehingga ada folder `patches/`).
2. Jalankan patcher:

   Windows (CMD):
     > python patches\retrofit_patcher.py

   PowerShell:
     PS> python .\patches\retrofit_patcher.py

   Git Bash/WSL:
     $ python patches/retrofit_patcher.py

3. Cek hasil:
     $ python patches/verify_retrofit.py

4. Tes lagi smoke:
     $ export PYTHONPATH="$(pwd)"
     $ python scripts/smoke_deep.py

Catatan
-------
- Patch ini tidak menyentuh config/token dan hanya menambah helper no-op.
- Aman dijalankan berkali-kali (idempotent). Selalu membuat backup .bak-<epoch> saat mengubah file.
- Jika masih ada cog lain yang minta API tambahan, tinggal tambahkan di fungsi `retrofit()`.
