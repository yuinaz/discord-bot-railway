
# SatpamBot Patches (Render + mini-PC)

This bundle fixes:
- async setup warnings (`add_cog` not awaited) for several cogs
- makes `/clearchat` allowed in public channels (global slash-check)
- sanitizes miner accel factors to avoid `ValueError: could not convert string to float: '0.85,'`
- provides a clean `local.json` that works on both Render and mini-PC

## Install
1. Copy `patches/` into your project at:
   `satpambot/bot/modules/discord_bot/cogs/patches/`
   (Create the `patches` folder if it doesn't exist.)

2. Replace your `local.json` with the one in this bundle, or merge manually.

3. Ensure ENV (Render):
   ```
   HOTENV_ENABLE=1
   SATPAMBOT_ENV_FILE=/opt/render/project/src/SatpamBot.env
   NEURO_GOVERNOR_ENABLE=1
   SELFHEAL_ENABLE=1
   SELFHEAL_AUTOFIX=1
   SELFHEAL_CRITICAL_ONLY=0
   ```

4. Restart the bot. On boot, you should see logs that the `preload` overlays are imported
   before other cogs. `/clearchat` should now work in public channels (with mod role).

## Notes
- If you still see "has no setup function" warnings, the patched async `setup()` will be used instead.
- `a02_miner_accel_overlay` is excluded; timing is handled by other overlays + the safe sanitizer.
- You can tweak miner accel via ENV:
  - `SATPAMBOT_MINER_ACCEL_TEXT`, `SATPAMBOT_MINER_ACCEL_PHISH`, `SATPAMBOT_MINER_ACCEL_SLANG`
  Trailing commas/whitespace will be ignored.
