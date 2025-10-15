import importlib
print("== import bootstrap phase0 + bootstrap ==")
importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a00_overlay_bootstrap")
print("== try import tts_voice_reply ==")
m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.tts_voice_reply")
print("module imported:", m is not None)
print("has setup:", hasattr(m, "setup"))
print("OK")
