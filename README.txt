Auto Role Anywhere — with Thread Sweeper + Channel Backfill (NO ENV)
-------------------------------------------------------------------
Fitur:
- THREAD SWEEPER: join & fetch member thread (butuh Manage Threads), beri role add-only.
- CHANNEL BACKFILL: scan author unik dari riwayat pesan text channel (Read Message History), beri role add-only.
- /roleauto backfill [limit]: jalankan backfill manual di channel/thread saat ini (ephemeral reply).

Konstanta (ubah di file jika perlu):
- THREAD_SWEEP_SECONDS=600
- CHANNEL_SWEEP_SECONDS=900
- CHANNEL_BACKFILL_LIMIT=400

Izin:
- Role bot di atas semua role game; Manage Roles.
- Parent forum: View Channel + Manage Threads (Send Messages in Posts boleh OFF).
- Text channel (wuwa-chat/hsr-chat): View Channel + Read Message History.
- Channel log (jika dipakai untuk fitur lain): Send Messages ON.

Files:
- config/auto_role_anywhere.json
- satpambot/bot/modules/discord_bot/cogs/auto_role_anywhere.py
