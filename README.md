# Leina Super Fix Bundle

All-in-one patch to harden your bot on Render free plan and eliminate the
`NoneType`/JSON/Upstash issues plus the curriculum & state checkpoint crashes.

## What's inside
- Robust Upstash client and readers (no more `.get` on None).
- Presence reads from `learning:status_json` as single source of truth.
- Learning writer uses `/pipeline`, supports `XP_SENIOR_KEY`, and **anti-downgrade**.
- Guard cog to restore label if any module writes lower rank.
- TK/SD curriculum cog with `_load_cfg()` for `a24` compatibility.
- Autopin/status overlays that don't crash on missing data.
- `discord_state_io` with `import_state/export_state/apply_state` (no-op safe).
- `xp_state_discord` parser that never returns None.
- Tolerant JSON helpers (`tolerant_loads/dumps`) accepting arbitrary kwargs.
- Refresher script accepting `--xp-key`, with ladder compute fix.
- XP test kit & smoketests.

## Recommended env
```
KV_BACKEND=upstash_rest
UPSTASH_REDIS_REST_URL=...
UPSTASH_REDIS_REST_TOKEN=...
LADDER_FILE=/g/DiscordBot/SatpamLeina/data/neuro-lite/ladder.json
XP_SENIOR_KEY=xp:bot:senior_total_v2
LEARNING_MIN_LABEL=KULIAH-S2
LEINA_PRESENCE_TEMPLATE=🎓 {label} • {percent:.1f}%
LEINA_PRESENCE_PERIOD_SEC=60
LEINA_PRESENCE_STATUS=online
LEINA_CURRICULUM_CHANNEL_ID=<channel_id>  # required for a20/a24 autopin
LEARNING_STATUS_CHANNEL_ID=<channel_id>   # optional for a08 status autopin
```

## Install
1) Extract to your repo root (paths must match).
2) Migrate XP to new key (optional but recommended):
   ```bash
   curl -sS -X POST "$UPSTASH_REDIS_REST_URL/pipeline" \
     -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
     -H "Content-Type: application/json" \
     -d '[["GET","xp:bot:senior_total"]]'
   curl -sS -X POST "$UPSTASH_REDIS_REST_URL/pipeline" \
     -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
     -H "Content-Type: application/json" \
     -d '[["SET","xp:bot:senior_total_v2","<value>"]]'
   ```
3) Prime live status once:
   ```bash
   python scripts/refresh_learning_status.py --write --xp-key xp:bot:senior_total_v2
   ```
4) Restart your bot with the same env.

## Quick smoketests
```bash
python tests/smoke_imports.py
python scripts/xp_test/simulate_senior_progress.py
python scripts/xp_test/whatif_label.py --xp 82290
```
