# Hotfix v3: Lindungi PHASH DB & STATUS di #log + Presence/Neuro Keeper

## Apa yang diperbaiki
- **Tidak boleh terhapus** lagi untuk pesan ber-marker:
  - `SATPAMBOT_PHASH_DB_V1`
  - `SATPAMBOT_STATUS_V1`
- Auto-delete log **hanya** menyapu pesan **sesi ini** dan **mengabaikan** pesan ber-marker di atas.
- Presence/keeper di thread **neuro-lite progress** tetap aman (pinned & upsert).

## File
- `cogs/delete_safe_shim_plus.py` — proteksi hapus (pinned, keeper neuro, log pre-session, **markers**).
- `cogs/log_autodelete_scoped.py` — auto-delete log **session-scope** + **skip markers**.
- `cogs/log_keeper_upserter.py` — memastikan pesan ber-marker **dipin** otomatis di `LOG_CHANNEL_ID`.
- (opsi) bila butuh presence upserter di thread neuro, gunakan juga patch sebelumnya (`neuro_presence_upserter.py`).

## ENV
- `LOG_CHANNEL_ID` (wajib) — id channel `#log-botphising`.
- `LOG_PROTECT_MARKERS` (opsional) — default: `SATPAMBOT_PHASH_DB_V1,SATPAMBOT_STATUS_V1`.
- `NEURO_THREAD_NAME` (opsional) — default: `neuro-lite progress`.
- `LOG_AUTODELETE_ENABLE` (default 1), `LOG_AUTODELETE_TTL` (900), `LOG_AUTODELETE_SCAN_EVERY` (30).

## Pasang
1. Salin berkas ke `satpambot/bot/modules/discord_bot/cogs/`.
2. Pastikan ketiga cogs **dimuat** oleh loader.
3. Set ENV sesuai dan **restart** bot.

## Verifikasi
- Cek log:
  - `[delete_safe_plus] Message.delete patched (pinned+keeper+session log protect+markers)`
  - `[log_keeper_upserter] pinned SATPAMBOT_PHASH_DB_V1` (atau STATUS)
- Di `#log-botphising`, pesan **SATPAMBOT_PHASH_DB_V1** dan **SATPAMBOT_STATUS_V1** harus **pinned** & tidak tersapu.
