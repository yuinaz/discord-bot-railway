# Fix Threads v3 (stop duplicate 'neuro-lite progress' + ensure JSON pinned)

**Perbaikan**
- `a00_thread_create_guard_shim.py`: mencegah duplikasi thread dengan **re-use** berdasarkan nama (cek aktif & arsip) secara global.
- `neuro_memory_pinner.py` v3: fallback ke `send()+pin` jika `message_keeper` tidak tersedia → JSON tetap muncul & dipin.
- `helpers/thread_utils.py`: pencarian arsip lebih kuat (mencoba beberapa iterator).

**Instruksi**
1. Salin file ke repo sesuai path.
2. Pastikan loader memuat:
   - `satpambot.bot.modules.discord_bot.cogs.a00_thread_create_guard_shim`
   - `satpambot.bot.modules.discord_bot.cogs.neuro_memory_pinner`
3. Deploy / restart.

**Catatan**
- Tidak perlu reply apa pun di channel log. Pinner akan posting langsung di **thread** 'neuro-lite progress'.
