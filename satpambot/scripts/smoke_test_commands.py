"""
Smoke test: load cogs locally (no Discord connection) and check commands & listeners.
This version auto-detects project root so you don't need PYTHONPATH.
Usage:
  python scripts/smoke_test_commands.py
"""
import asyncio
import sys
import inspect
from pathlib import Path

# Auto-add project root (parent of scripts/) to sys.path
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Allow running from project root or via scripts/
try:
    from satpambot.bot.modules.discord_bot.discord_bot import SatpamBot  # type: ignore
    from satpambot.bot.modules.discord_bot.cogs_loader import load_all_cogs  # type: ignore
except Exception as e:
    print("❌ Import failed:", e)
    print("Hint: ensure this file is inside <project>/scripts/ and run: python scripts/smoke_test_commands.py")
    raise

import discord

async def main():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True

    bot = SatpamBot(command_prefix="!", intents=intents, case_insensitive=True)
    await load_all_cogs(bot)  # manual instead of setup_hook

    cmds = sorted([c.qualified_name for c in bot.commands])
    print("✅ Commands registered:", cmds)
    required = {"status","serverinfo","testban","ban","unban"}
    missing = sorted(list(required - set(cmds)))
    if missing:
        print("❌ Missing commands:", missing)
        raise SystemExit(2)
    else:
        print("✅ All required commands present.")

    # Check duplicate listeners for on_message
    listeners = bot.extra_events.get("on_message", [])
    print(f"ℹ️ on_message listeners count = {len(listeners)}")
    if len(listeners) > 1:
        print("⚠️ More than one on_message listener registered. Ensure only one custom listener is added.")
    else:
        print("✅ Single on_message listener.")

if __name__ == "__main__":
    asyncio.run(main())
