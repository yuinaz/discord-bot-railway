
# smoketest: import cogs & helper
import importlib, os

mods = [
    "satpambot.bot.modules.discord_bot.helpers.progress_gate",
    "satpambot.bot.modules.discord_bot.cogs.public_mode_gate",
    "satpambot.bot.modules.discord_bot.cogs.learning_progress_reporter",
]
ok = True
for m in mods:
    try:
        importlib.import_module(m)
        print(f"[OK] import: {m}")
    except Exception as e:
        print(f"[FAIL] {m}: {e}")
        ok = False

if ok:
    # quick functional check
    from satpambot.bot.modules.discord_bot.helpers import progress_gate as gate
    os.environ["PUBLIC_MIN_PROGRESS"] = "1.0"
    os.environ["SILENT_PUBLIC"] = "1"  # default block
    os.environ["PROGRESS_VALUE"] = "1.0"
    assert gate.is_public_allowed() is True, "public should be allowed when ratio==1.0 and SILENT_PUBLIC set to 1 but runtime open False? guard returns True due to threshold + SILENT_PUBLIC handling"
    gate.set_public_open(False)
    print("-- Sanity check passed --")
