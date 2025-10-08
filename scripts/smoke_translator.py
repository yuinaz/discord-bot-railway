
import importlib, sys, pathlib

# ensure repo root on sys.path (scripts/ -> root)
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def check(modname: str):
    try:
        importlib.import_module(modname)
        print(f"[OK] import: {modname}")
    except Exception as e:
        print(f"[FAIL] {modname}: {e}")

check("satpambot.utils.translate_utils")
check("satpambot.bot.modules.discord_bot.cogs.translator")
check("satpambot.bot.modules.discord_bot.cogs.warn_reaction_blocker")
print("-- OK if translate modules show [OK]")
