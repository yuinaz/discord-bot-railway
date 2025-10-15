import importlib
print("== import overlay bootstrap ==")
importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a00_overlay_bootstrap")
print("== miner patched values ==")
mods = [
  "satpambot.bot.modules.discord_bot.cogs.text_activity_hourly_miner",
  "satpambot.bot.modules.discord_bot.cogs.slang_hourly_miner",
  "satpambot.bot.modules.discord_bot.cogs.phish_text_hourly_miner",
]
for mname in mods:
  m = importlib.import_module(mname)
  vals = {k:getattr(m,k,None) for k in ["START_DELAY_SEC","PERIOD_SEC","PER_CHANNEL","TOTAL_BUDGET","SKIP_MOD"]}
  print(mname.split(".")[-1], vals)
print("OK")
