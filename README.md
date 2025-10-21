# Ban Offloader & Muzzle Helper

## Runtime overlay (recommended)
Copy `satpambot/bot/modules/discord_bot/cogs/a00_disable_ban_overlay.py` into your repo and restart.
It removes **ban / tban / tempban / unban** (text & slash) at runtime and blocks any leftover calls.

## One-shot scripts
- `scripts/disable_ban_modules.py` → rename ban cogs and disable unban in `admin.py`.
  Usage:
  ```bash
  python scripts/disable_ban_modules.py
  ```
- `scripts/set_dm_muzzle_off.py` → writes top-level `DM_MUZZLE: "off"` into `local.json`.
  Usage:
  ```bash
  python scripts/set_dm_muzzle_off.py
  ```

## Notes
- Your current `local.json` contains nested `"dm_muzzle": {"mode":"owner"}`. The runtime config uses top-level `DM_MUZZLE`. 
  Run `scripts/set_dm_muzzle_off.py` or set environment variable `DM_MUZZLE=off` in Render to silence DM redirects.
