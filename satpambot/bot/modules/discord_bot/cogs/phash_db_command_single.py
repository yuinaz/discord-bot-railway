
import os, json, datetime as dt
import discord
from discord.ext import commands
from satpambot.bot.utils.embed_scribe import EmbedScribe
from satpambot.bot.utils.dupe_guard import DuplicateSuppressor
from satpambot.config.compat_conf import get as cfg

PHASH_PATH = cfg("SATPAMBOT_PHASH_DB_V1_PATH", "data/phash/SATPAMBOT_PHASH_DB_V1.json", str)
EMBED_KEY = "phash_db_v1"
ENABLE = bool(cfg("PHASH_DB_SINGLE_COMMAND", True, bool))

def _ensure_file():
    os.makedirs(os.path.dirname(PHASH_PATH), exist_ok=True)
    if not os.path.exists(PHASH_PATH):
        with open(PHASH_PATH, "w", encoding="utf-8") as f:
            json.dump({"phash": []}, f)

def _load():
    _ensure_file()
    try:
        with open(PHASH_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"phash": []}

class PhashDBSingle(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scribe = EmbedScribe(bot)
        self.dupe = DuplicateSuppressor(ttl_seconds=60)

    @commands.command(name="phash_db")
    async def phash_db(self, ctx: commands.Context):
        if not ENABLE:
            return
        db = _load()
        cnt = len(db.get("phash", []))
        e = discord.Embed(title="SATPAMBOT_PHASH_DB_V1",
            description=f"`count: {cnt}`", color=discord.Color.dark_teal())
        e.add_field(name="Preview", value="```json\n" + json.dumps({"phash": db.get("phash", [])[:6]}, indent=2) + "\n```", inline=False)
        e.set_footer(text=f"key:{EMBED_KEY} • updated {dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}Z")
        ch = ctx.channel
        payload_sig = f"{cnt}|{e.footer.text}"
        if not self.dupe.should_skip(ch.id, EMBED_KEY, payload_sig):
            await self.scribe.upsert(ch, EMBED_KEY, e, pin=False)
        try: await ctx.message.add_reaction("📘")
        except Exception: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashDBSingle(bot))
