
from discord.ext import commands
def _get_conf():
    try:
        from satpambot.config.compat_conf import get_conf
        return get_conf
    except Exception:
        try:
            from satpambot.config.runtime_memory import get_conf
            return get_conf
        except Exception:
            def _f(): return {}
            return _f

import discord, json

from pathlib import Path
from satpambot.bot.utils import embed_scribe

class PhashDbCommandSingle(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.path = _get_conf()().get("SATPAMBOT_PHASH_DB_V1_PATH", "data/phash/SATPAMBOT_PHASH_DB_V1.json")

    @commands.command(name="phashdb")
    async def phashdb(self, ctx: commands.Context):
        p = Path(self.path)
        data = {"version":"1","items":[]}
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        items = data.get("items", [])
        e = discord.Embed(title="SATPAMBOT_PHASH_DB_V1", description=f"Total **{len(items)}** entries", color=0x95a5a6)
        await embed_scribe.upsert(ctx.channel, "SATPAMBOT_PHASH_DB_V1", e, pin=True, bot=self.bot, route=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(PhashDbCommandSingle(bot))