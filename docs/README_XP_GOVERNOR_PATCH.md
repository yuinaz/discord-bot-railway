
# Leina — XP + Governor Patch Pack (Render Free Friendly)

## Isi
- `satpambot/bot/modules/discord_bot/cogs/a08_xp_upstash_verbose_overlay.py`
- `satpambot/bot/modules/discord_bot/cogs/a08_xp_senior_detail_reporter.py`
- `satpambot/tools/export_xp_to_upstash.py`
- `config/governor.local.json.example`

## ENV minimum (Render → Environment)
```
UPSTASH_REDIS_REST_URL=...
UPSTASH_REDIS_REST_TOKEN=...
XP_UPSTASH_VERBOSE=1

# Optional log event
XP_UPSTASH_EVENTS_ENABLE=0
XP_UPSTASH_EVENTS_MAX=1000
XP_UPSTASH_EVENT_SAMPLE=10

# Aggregator
SENIOR_L1_TARGET=2000
SENIOR_DETAIL_INTERVAL=300
SENIOR_DETAIL_TOPN=10

# Governor (contoh)
NEURO_GOVERNOR_ENABLE=1
GOV_REQUIRE_QNA_APPROVAL=True
GOV_MIN_DAYS=7
GOV_MIN_XP=2500
GOV_MATURE_ERR_RATE=0.03
QNA_CHANNEL_ID=<ID QNA>
NEURO_GOVERNOR_OWNERS=<CSV owner IDs atau simpan di local.json>
```

## Folder data
- Bot tetap menggunakan `data/neuro-lite/` untuk snapshot bridge dan progress.
- Patch ini **tidak mengubah** struktur lokal. Exporter bisa membaca `data/neuro-lite/bridge_senior.json` jika dipilih `--from-bridge`.

## Cara Pasang (singkat)
1. Salin semua file ke repo:
   - cogs → `satpambot/bot/modules/discord_bot/cogs/`
   - tool → `satpambot/tools/export_xp_to_upstash.py`
2. Set ENV (lihat atas).
3. Jalankan `/pullrepo` → restart bot.

## Export data ke Upstash (sekali jalan)
**Pilih salah satu sumber**:

- Dari key lama `xp:store` di Upstash:
```
python -m satpambot.tools.export_xp_to_upstash --from-upstash-store --reason import --l1 2000
```

- Dari file JSON lokal (map `{uid:int}` atau daftar event `{uid,delta,reason}`):
```
python -m satpambot.tools.export_xp_to_upstash --from-json data/xp_snapshot.json --reason import --l1 2000
```

- Dari bridge lokal:
```
python -m satpambot.tools.export_xp_to_upstash --from-bridge --reason import --l1 2000
```

Exporter akan menulis:
- `xp:bucket:senior:users` (per user)
- `xp:bucket:reasons` (pakai alasan `--reason`)
- `xp:u:<uid>` (total per user)
- `xp:bot:senior_total` (INT)
- `xp:bot:senior_detail` (JSON)

## Query verifikasi (Upstash Console)
```
GET xp:bot:senior_total
GET xp:bot:senior_detail
HGETALL xp:bucket:senior:users
HGETALL xp:bucket:reasons
```

## Catatan Render Free
- Semua request ke Upstash digabung **pipeline** untuk hemat kuota.
- Aggregator jalan tiap 5 menit (ubah `SENIOR_DETAIL_INTERVAL`).

