import discord
from discord.ext import commands
try:
    from satpambot.config.compat_conf import get_conf  # prefer new compat layer
except Exception:  # pragma: no cover
    try:
        from satpambot.config.runtime_memory import get_conf  # fallback older projects
    except Exception:
        def get_conf():
            return {}
from satpambot.bot.utils import phash_db as PDB
from satpambot.bot.utils import embed_scribe

class PhashDbCommandSingle(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.path = get_conf().get("SATPAMBOT_PHASH_DB_V1_PATH", "data/phash/SATPAMBOT_PHASH_DB_V1.json")

    @commands.command(name="phashdb")
    async def phashdb(self, ctx: commands.Context):
        db = PDB.load_db(self.path)
        items = db.get("items", [])
        e = discord.Embed(title="SATPAMBOT_PHASH_DB_V1", color=0x95a5a6,
                          description=f"Total images: **{len(items)}**")
        await embed_scribe.upsert(ctx.channel, "SATPAMBOT_PHASH_DB_V1", e, pin=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashDbCommandSingle(bot))
