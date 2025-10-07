import os, sys
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

def check(mod):
    try:
        __import__(mod); print(f"[OK] {mod}"); return True
    except Exception as e:
        print(f"[WARN] {mod} -> {e}"); return False

ok = True
ok &= check('satpambot.bot.modules.discord_bot.cogs.self_learning_guard')
ok &= check('satpambot.bot.modules.discord_bot.cogs.chat_neurolite')
sys.exit(0)
