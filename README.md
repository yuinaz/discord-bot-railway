# Leina — Final Fix Bundle

Semua patch dalam satu paket, untuk mencegah mismatch label (SMP-L1) dan memastikan
render status mengikuti `ladder.json` + Upstash sebagai sumber kebenaran.

## Isi
```
satpambot/bot/modules/discord_bot/cogs/a00_learning_status_refresh_overlay.py
satpambot/bot/modules/discord_bot/cogs/a09_presence_from_upstash_overlay.py
satpambot/bot/modules/discord_bot/cogs/a98_learning_status_guard.py
satpambot/bot/modules/discord_bot/cogs/a20_curriculum_tk_sd.py
satpambot/bot/modules/discord_bot/helpers/upstash_client.py
satpambot/bot/modules/discord_bot/helpers/ladder_loader.py
satpambot/bot/modules/discord_bot/helpers/rank_utils.py
scripts/refresh_learning_status.py
scripts/xp_test/...
```

## Env yang direkomendasi
```
# Upstash
KV_BACKEND=upstash_rest
UPSTASH_REDIS_REST_URL=...
UPSTASH_REDIS_REST_TOKEN=...

# Ladder canonical
LADDER_FILE=/g/DiscordBot/SatpamLeina/data/neuro-lite/ladder.json

# XP key terisolasi
XP_SENIOR_KEY=xp:bot:senior_total_v2

# Anti-downgrade minimal
LEARNING_MIN_LABEL=KULIAH-S2
```

## Urutan update
1. Extract zip ke repo kamu (timpa file yang ada).
2. Migrasi XP ke key baru (opsional tapi disarankan):
   ```bash
   curl -sS -X POST "$UPSTASH_REDIS_REST_URL/pipeline" \
     -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
     -H "Content-Type: application/json" \
     -d '[["GET","xp:bot:senior_total"]]'
   # lalu set ke key baru:
   curl -sS -X POST "$UPSTASH_REDIS_REST_URL/pipeline" \
     -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
     -H "Content-Type: application/json" \
     -d '[["SET","xp:bot:senior_total_v2","<angka_xp>"]]'
   ```
3. Tulis status sekali via script:
   ```bash
   python scripts/refresh_learning_status.py --write --xp-key xp:bot:senior_total_v2
   ```
4. Jalankan bot (pastikan env yang sama dipakai proses bot).
5. (Opsional) Nonaktifkan modul lama yang menulis `learning:status_json` agar tidak balapan.

## Verifikasi cepat
```bash
# live label
curl -sS -X POST "$UPSTASH_REDIS_REST_URL/pipeline" \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[["GET","learning:status"],["GET","learning:status_json"],["GET","learning:phase"]]'
# test kit
python scripts/xp_test/verify_current_vs_upstash.py
```
