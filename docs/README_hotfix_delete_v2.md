# Hotfix: Protect Neuro Thread from Deletions (v2)

**Kenapa?** `chat_neurolite_guard` masih menghapus pesan bot di thread *neuro-lite progress*, sehingga keeper JSON langsung hilang.

**Apa yang dilakukan hotfix ini?**
- Membungkus `discord.Message.delete` untuk:
  - Mengabaikan NotFound(10008)/Forbidden (tetap ada seperti v1).
  - **MENGABAIKAN** penghapusan untuk pesan di thread **neuro-lite progress** atau yang kontennya terlihat seperti **keeper**:
    - mengandung `NEURO-LITE MEMORY`, atau
    - `NEURO-LITE GATE STATUS`, atau
    - prefix key `[neuro-lite:`.

**Cara pakai**
1. Timpa file: `satpambot/bot/modules/discord_bot/cogs/delete_safe_shim.py`.
2. Pastikan cog ini dimuat lebih awal dari `chat_neurolite_guard` (umumnya sudah).
3. Restart bot. Keeper JSON di thread *neuro-lite progress* akan **tetap bertahan**.

**Catatan**
- Ini proteksi di level global; bila ingin granular, nanti bisa kita ganti jadi daftar whitelist channel/thread ID via ENV.
