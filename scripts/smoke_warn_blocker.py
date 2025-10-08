
import importlib, sys, pathlib, os

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Optional envs for quick test
os.environ.setdefault("WARN_REACTION_BLOCKLIST", "⚠️,⚠")
os.environ.setdefault("WARN_REACTION_REMOVE_DELAY_S", "0.0")

try:
    importlib.import_module("satpambot.bot.modules.discord_bot.cogs.warn_reaction_blocker")
    print("[OK] import: satpambot.bot.modules.discord_bot.cogs.warn_reaction_blocker")
except Exception as e:
    print("[FAIL] satpambot.bot.modules.discord_bot.cogs.warn_reaction_blocker:", e)
