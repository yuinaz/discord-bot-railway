# SatpamBot — Translator Patch

**Date:** 2025-10-07 14:05:32

This patch fixes the `No module named 'satpambot'` error in `scripts/smoke_translator.py` and
adds a safe, import-only translator Cog and utility.

## What’s inside

```
satpambot/
  __init__.py
  utils/
    __init__.py
    translate_utils.py
  bot/modules/discord_bot/cogs/
    __init__.py
    translator.py
scripts/
  smoke_translator.py
```

## How to apply

1. **Extract** the zip at the **repository root** (same folder that contains `satpambot/` and `scripts/`).  
2. (Optional but recommended) Install/ensure deps:
   - `googletrans-py>=4.0.0`
   - `deep-translator>=1.11.4`

   ```bash
   python -m pip install -U googletrans-py deep-translator
   ```

3. **Run the smoke test** from repo root:

   ```bash
   python scripts/smoke_translator.py
   ```

   You should see:
   ```
   [OK] satpambot.utils.translate_utils: import ok
   [OK] satpambot.bot.modules.discord_bot.cogs.translator: import ok
   -- OK if both above show [OK]
   ```

4. **Load the Cog** (when you actually run the bot) like your other cogs (e.g. via your dynamic loader). The Cog is safe on import and won’t do anything until added to the bot.

## Notes

- `translate_utils.translate_text(text, target_lang="id", source_lang="auto")` lazily imports providers and
  falls back between `googletrans` and `deep_translator` so your import-based smoke tests remain fast and offline‑friendly.
- If you still see `No module named 'satpambot'`, ensure you are running commands **from the repo root** or that the root is on `PYTHONPATH`.
