# Neuro Progress Patch

**Tujuan**
1) **Hentikan** spam membuat thread baru *"neuro-lite progress"* setiap boot — kita **reuse** yang sudah ada (aktif/arsip).
2) **Upsert + pin** pesan *keeper* berisi **memory JSON** (mis. `data/learn_progress_junior.json`) di thread *"neuro-lite progress"*.

## File baru
- `satpambot/bot/modules/discord_bot/helpers/thread_utils.py`
  > Util umum: cari log channel (`LOG_CHANNEL_ID` → nama → fallback) dan cari/buat thread *"neuro-lite progress"* (cek aktif & arsip).
- `satpambot/bot/modules/discord_bot/cogs/progress_thread_reuse_shim.py`
  > Shim kecil yang memaksa `LearningProgress.ensure_thread()` **mencari thread by name dulu**, baru membuat jika benar-benar tidak ada.
- `satpambot/bot/modules/discord_bot/cogs/neuro_memory_pinner.py`
  > Cog yang **upsert** pesan keeper dengan key `[neuro-lite:memory]` dan **pin** ke thread. Otomatis jalan saat boot dan watch tiap 10 menit.
- `scripts/smoke_neuro_progress.py`
  > Smoke test ringan untuk validasi `data/learn_progress_junior.json`.

## Instalasi
1. Copy semua file patch ke repo mengikuti path-nya.
2. Commit → deploy / restart.
3. Pastikan **ENV** `LOG_CHANNEL_ID` sudah benar (dari log kamu: `1400375184048787566` → `#log-botphising`).

## Verifikasi
- Saat bot online:
  - **Tidak** ada thread *neuro-lite progress* baru bila sudah ada yang lama (aktif/arsip).
  - Di thread tersebut ada 1 pesan **pinned** bertajuk **NEURO-LITE MEMORY** dengan blok ```json ...```.
  - Jika `data/learn_progress_junior.json` berubah, pesan akan ikut ter-update (cek setiap 10 menit).

## Catatan
- Patch ini **tidak** menghapus/ubah file existing (aman). Bila mau, kamu bisa menonaktifkan patch dengan mematikan kedua cog baru di `cogs_loader`.
- Untuk sumber memory lain, tambahkan path-nya di `MEM_PATHS` dalam `neuro_memory_pinner.py`.
