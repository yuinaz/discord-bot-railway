
# SatpamBot ENV Import Patch

Import semua variable dari `SatpamBot.env` ke **memori bot** (persist ke `satpambot_config.local.json`), termasuk API keys, token, OWNER_USER_ID, channel ID, dll.

## File yang ditambahkan
- `sitecustomize.py` — auto-import `SatpamBot.env` saat start (hanya jika file berubah).
- `satpambot/config/runtime.py` — store config internal + `set_secret()`.
- `satpambot/config/env_importer.py` — parser .env dan importer.
- `scripts/import_env_to_config.py` — CLI sekali jalan (opsional).

## Cara pakai
1. Taruh file **`SatpamBot.env`** di root repo.
2. Start bot seperti biasa → otomatis **import**.
   - Atau manual: `python scripts/import_env_to_config.py SatpamBot.env`
3. Cek hasil via DM ke bot: `config show` (secrets tidak ditampilkan nilainya).
