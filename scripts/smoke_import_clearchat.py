import importlib, sys
REQS = [
    "satpambot.bot.modules.discord_bot.cogs.clearchat",
    "satpambot.bot.modules.discord_bot.cogs.clearchat_tbstyle",
]
ok = True
for m in REQS:
    try:
        importlib.import_module(m)
        print("[OK] import", m)
    except Exception as e:
        print("[FAIL]", m, "=>", e)
        ok = False
sys.exit(0 if ok else 1)
