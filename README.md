# Leina Fix — Presence from Upstash (No More SMP-L1)

This overlay **reads `learning:status_json` from Upstash** and renders presence
from that single source of truth. If the key is missing, it **falls back** to
computing from `xp:bot:senior_total` using your canonical ladder file:
`data/neuro-lite/ladder.json` (or `LADDER_FILE`).

Why this fixes your issue:
- Your Upstash already says `KULIAH-S2`, but some modules were recomputing and
  showing `SMP-L1`. This overlay **does not recompute** when `learning:status_json`
  exists — it **uses it directly**, so display stays consistent.
- It only writes to Discord presence (does not overwrite Upstash keys).

## Install
Extract into your repo so paths look like:
```
satpambot/bot/modules/discord_bot/cogs/a09_presence_from_upstash_overlay.py
satpambot/bot/modules/discord_bot/helpers/upstash_client.py
satpambot/bot/modules/discord_bot/helpers/ladder_loader.py
```

Ensure these env vars are set *in the process that runs the bot*:
```
KV_BACKEND=upstash_rest
UPSTASH_REDIS_REST_URL=...
UPSTASH_REDIS_REST_TOKEN=...
LADDER_FILE=/g/DiscordBot/SatpamLeina/data/neuro-lite/ladder.json
LEARNING_MIN_LABEL=KULIAH-S2
```

## Enable
Your extension loader should auto-load `a09_*.py`. If not, add it to your
cogs list. The overlay updates presence only when value changes.

## Optional env
```
LEINA_PRESENCE_TEMPLATE=🎓 {label} • {percent:.1f}%
LEINA_PRESENCE_PERIOD_SEC=60
LEINA_PRESENCE_STATUS=online   # online | idle | dnd | invisible
LEINA_PRESENCE_DISABLE=        # set to 1 to disable
```
