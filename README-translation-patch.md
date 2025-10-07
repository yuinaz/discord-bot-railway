# SatpamBot — Translation Patch

What you get:
- `requirements.latest.txt` with translation deps:
  - `googletrans-py` (primary), `deep-translator` + `langdetect` (fallbacks)
- `satpambot/extra/translate_utils.py` — simple wrapper
- `satpambot/bot/modules/discord_bot/cogs/translator.py` — slash+prefix+context menu+reaction

How to install (Git Bash / Windows / Render):

```bash
# In repo root:
unzip satpambot-translation-patch.zip -d .

# Install deps (pick your Python):
python -m pip install -r requirements.latest.txt
# or:
python3 -m pip install -r requirements.latest.txt

# Quick smoke (offline-safe)
python scripts/smoke_translator.py
```

How to use in Discord:
- Slash: `/tr text:<kalimat> to:<id|en|ja|zh-cn>`
- Prefix: `tr en: halo dunia`
- Context menu: right-click a message → Apps → Translate …
- React to a message with 🇮🇩 🇺🇸 🇯🇵 🇨🇳 to auto-reply with translation.
