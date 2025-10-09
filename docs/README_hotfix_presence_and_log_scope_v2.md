# Hotfix: Presence Protect + Log Auto-Delete (Session-Only)

## Tujuan
- **Pinned & keeper** (`presence::keeper`, `neuro-memory::keeper`) **tidak pernah terhapus**.
- **Auto-delete log** hanya menyapu **pesan sesi saat ini** (lahir setelah bot online).
- Presence di thread **neuro-lite progress** di-**upsert** (edit) bukan bikin duplikat, dan **dipin**.

## File
- `cogs/delete_safe_shim_plus.py` — Monkeypatch `Message.delete` dengan proteksi:
  - Protect pinned
  - Protect keeper di thread neuro
  - Protect log lama (pre-session) di channel `LOG_CHANNEL_ID`
- `cogs/log_autodelete_scoped.py` — Auto-delete log **session-scope**, TTL via ENV (default 900s).
- `cogs/neuro_presence_upserter.py` — Menjamin pinned presence 1x per thread neuro (upsert).

## ENV
- `LOG_CHANNEL_ID` (wajib untuk log_autodelete_scoped)
- `NEURO_THREAD_NAME` (default: `neuro-lite progress`)
- `LOG_AUTODELETE_ENABLE` (default: `1` / True)
- `LOG_AUTODELETE_TTL` (detik, default: `900`)
- `LOG_AUTODELETE_SCAN_EVERY` (detik, default: `30`)

## Pasang
1. Salin folder `satpambot/bot/modules/discord_bot/cogs/*.py` ke repo.
2. Muat cogs ini (via daftar cogs atau cogs_loader).
3. Set ENV sesuai di atas → **restart**.
4. Verifikasi log:
   - `[delete_safe_plus] Message.delete patched ...`
   - `[log_autodelete_scoped] ...` (enabled, scan jalan)
   - `[presence_upserter] created/update presence keeper`

## Catatan
- Patch ini **tidak** menyentuh pesan yang lahir **sebelum** bot online ketika menyapu log (session-scope).
- Jika sebelumnya ada cog `log_autodelete_bot` yang menyapu global, biarkan guard ini menolak delete untuk pre-session (aman), atau nonaktifkan cog tersebut.
