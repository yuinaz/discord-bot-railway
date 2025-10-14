# Learning Scope Filter Patch (denylist by channel/category + threads/forums toggles)

Patch ini **memaksa penyaringan scope learning** di level `upsert_pinned_memory` sehingga
snapshot dari miners akan **difilter** sesuai konfigurasi, apa pun implementasi miner-nya.

## Cara pasang
1. Ekstrak isi ZIP ini ke root repo SatpamBot (struktur `satpambot/...`, `scripts/...`).
2. **Ganti** file `satpambot/bot/modules/discord_bot/cogs/a00_overlay_bootstrap.py` dengan versi di patch ini
   (atau pastikan baris untuk memuat `a27_learning_scope_filter_overlay` ada).
3. Merge konfigurasi contoh (optional jika sudah kamu set di JSON):
   ```bash
   python -m scripts.merge_local_json learn_scope_exclude_ids.json
   ```
4. Restart bot, lalu cek log: harus muncul `[scope_filter]` dengan ringkasan jumlah item sebelum/sesudah filter saat pin.

## Kunci konfigurasi (dibaca via cfg())
- `LEARN_SCOPE`: `"denylist"` | `"allowlist"` | `"all"`
- `LEARN_BLACKLIST_CHANNELS`: daftar ID channel yang **tidak** boleh dipelajari
- `LEARN_BLACKLIST_CATEGORIES`: daftar ID kategori yang **tidak** boleh dipelajari
- `LEARN_WHITELIST_CHANNELS`: daftar ID channel yang boleh dipelajari (jika scope=allowlist)
- `LEARN_SCAN_PUBLIC_THREADS`: `true/false`
- `LEARN_SCAN_PRIVATE_THREADS`: `true/false`
- `LEARN_SCAN_FORUMS`: `true/false`

## Catatan
- Payload yang di-pin biasanya berbentuk dict dengan kunci `items` berisi list.
  Patch ini akan menghapus elemen yang `channel_id`-nya terlarang, atau elemen yang bertipe thread/forum
  sesuai toggle. Jika struktur berbeda, patch akan aman (no-op).
