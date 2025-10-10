# scripts/smoke_miner_timing.py
from importlib import import_module as _im

mods = {
    "text": "satpambot.bot.modules.discord_bot.cogs.text_activity_hourly_miner",
    "phish": "satpambot.bot.modules.discord_bot.cogs.phish_text_hourly_miner",
    "slang": "satpambot.bot.modules.discord_bot.cogs.slang_hourly_miner",
}
m = {k: _im(v) for k, v in mods.items()}
print("TEXT:", getattr(m["text"], "TEXT_START_DELAY_SEC", None), getattr(m["text"], "TEXT_PERIOD_SEC", None))
print("PHISH:", getattr(m["phish"], "START_DELAY_SEC", None), getattr(m["phish"], "PERIOD_SEC", None))
print("SLANG:", getattr(m["slang"], "START_DELAY_SEC", None), getattr(m["slang"], "PERIOD_SEC", None))
