# scripts/smoketest_ftab_bundle.py
import sys, pathlib, importlib

def add_repo_root():
    here = pathlib.Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "satpambot").exists():
            sys.path.insert(0, str(parent))
            return parent
    return None

root = add_repo_root()
if not root:
    print("IMPORT FAILED: cannot locate 'satpambot' folder upwards from", __file__)
    raise SystemExit(1)

mods = [
    "satpambot.bot.modules.discord_bot.cogs.first_touch_attachment_ban",
    "satpambot.bot.modules.discord_bot.cogs.first_touch_autoban_pack_mime",
]
for m in mods:
    mm = importlib.import_module(m)
    print("OK import:", mm.__name__)

print("BUNDLE OK from", root)
