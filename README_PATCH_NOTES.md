
# Patch Notes – 2025-08-11
- Fix `!tb` / `!testban` hanya kirim **1 embed** + stiker FibiLaugh fallback dari `assets/fibilaugh.png`.
- Perbaiki `on_ready` mengumumkan status **di semua guild** ke kanal `#log-botphising` (atau sesuai ENV), dan set presence bot.
- Tidak ada perubahan pada nama variabel ENV. Pastikan:
  - `BOT_TOKEN` terisi.
  - (Opsional) `LOG_CHANNEL_ID` atau `LOG_CHANNEL_NAME=log-botphising` sesuai server kamu.
