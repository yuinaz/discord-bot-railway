import importlib
print("== import overlay bootstrap ==")
importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a00_overlay_bootstrap")
print("== patched learning values (module vars) ==")
m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.learning_passive_observer")
for k in ["XP_WINDOW_SEC","XP_CAP_PER_WINDOW","MIN_DELTA_ITEMS",
          "XP_PER_ITEM_TEXT","XP_PER_ITEM_SLANG","XP_PER_ITEM_PHISH",
          "BURST_ON_BOOT","BURST_MULTIPLIER","BURST_DURATION_SEC"]:
    print(k, "=", getattr(m, k, None))
print("OK")
