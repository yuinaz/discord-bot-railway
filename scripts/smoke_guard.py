
# smoketest for silent guard import
import importlib, os, sys
sys.path.insert(0, os.getcwd())

os.environ.setdefault("SILENT_PUBLIC", "1")
os.environ.setdefault("ALLOW_DM", "1")
os.environ.setdefault("DISABLE_NAME_WAKE", "1")

try:
    importlib.import_module("satpambot.bot.modules.discord_bot.cogs.chat_neurolite_guard")
    print("[OK] import: satpambot.bot.modules.discord_bot.cogs.chat_neurolite_guard")
except Exception as e:
    print("[FAIL] chat_neurolite_guard:", e)
print("-- OK if chat_neurolite_guard shows [OK]")
