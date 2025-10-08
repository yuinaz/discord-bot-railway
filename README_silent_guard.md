
# Silent Guard for ChatNeuroLite (DM-only)

**Goal:** Bot tidak boleh membalas di channel publik sama sekali; DM tetap boleh.
Patch ini tidak mengubah config kamu — cukup tambahkan cog ini.

## File
- `satpambot/bot/modules/discord_bot/cogs/chat_neurolite_guard.py`
- `scripts/smoke_guard.py`

## Cara pakai
1. Salin file ke repo (struktur folder sama).
2. Jalankan smoke test:
   ```bash
   python scripts/smoke_guard.py
   ```
3. Deploy/start bot. Guard akan aktif otomatis.

## ENV (opsional)
- `SILENT_PUBLIC=1` (default) → blok semua balasan di guild/public.
- `ALLOW_DM=1` (default) → izinkan DM.
- `DISABLE_NAME_WAKE=1` (default) → matikan cogs name-wake.
- `PUBLIC_MIN_PROGRESS=101` → batas progres minimum untuk balas di publik
   (dibiarkan >100 agar selalu terblok saat fase belajar).
