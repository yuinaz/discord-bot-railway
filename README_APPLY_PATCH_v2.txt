
PATCH v2 (config-first, no Render ENV dependency)

✓ Semua setting dibaca dari file JSON dulu (prioritas 1), kalau tidak ada barulah ke ENV (prioritas 2).
File kandidat (cek berurutan): 
  - satpambot_config.local.json
  - config/satpambot_config.local.json
  - data/config/satpambot_config.local.json
  - satpambot.local.json

Contoh minimal satpambot_config.local.json:
{
  "PROGRESS_EMBED_CHANNEL_ID": 123456789012345678,
  "PROGRESS_EMBED_KEY": "daily_progress",
  "PROGRESS_EMBED_PIN": true,
  "NEURO_LITE_DIR": "data/neuro-lite",
  "NEURO_AUTO_INCREMENT": true,
  "NEURO_AUTO_INCREMENT_STEP": 0.25,
  "SATPAMBOT_PHASH_DB_V1_PATH": "data/phash/SATPAMBOT_PHASH_DB_V1.json",
  "PHASH_DB_SINGLE_COMMAND": true,
  "EMBED_SCRIBE_STATE": "data/state/embed_scribe.json"
}

Cogs yang perlu aktif:
  - satpambot.bot.modules.discord_bot.cogs.progress_embed_solo
  - satpambot.bot.modules.discord_bot.cogs.phash_db_command_single

Notes:
- Tidak wajib ENV Render lagi. Di MiniPC cukup taruh JSON di root repo (nama di atas). 
- Jika JSON tidak ada/invalid, sistem fallback ke ENV, lalu default.
