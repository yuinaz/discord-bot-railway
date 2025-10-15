
"""
Minimal sanity check for Render Free (no config changes).
- Imports critical cogs
- FakeBot runs async setup(bot) without network
"""
import asyncio, importlib, sys, types

class FakeBot:
    async def add_cog(self, cog):
        # accept any cog; no-op
        return True
    async def wait_until_ready(self):
        return

async def _load():
    bot = FakeBot()
    mods = [
        "satpambot.bot.modules.discord_bot.cogs.sticker_text_feedback",
        "satpambot.bot.modules.discord_bot.cogs.learning_progress",
    ]
    ok = True
    for m in mods:
        try:
            mod = importlib.import_module(m)
            setup = getattr(mod, "setup", None)
            if setup:
                await setup(bot)
        except Exception as e:
            print(f"FAIL: {m}: {e}", file=sys.stderr)
            ok = False
    return ok

def main():
    ok = asyncio.get_event_loop().run_until_complete(_load())
    print("PASS" if ok else "FAIL")

if __name__ == "__main__":
    main()
