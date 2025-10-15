
import datetime as dt
import discord
from discord.ext import commands, tasks

from satpambot.bot.utils.embed_scribe import EmbedScribe
from satpambot.bot.utils.dupe_guard import DuplicateSuppressor
from satpambot.ml import neuro_lite_memory_fix as nmem
from satpambot.config.compat_conf import get as cfg

TARGET_CHANNEL_ID = int(cfg("PROGRESS_EMBED_CHANNEL_ID", 0, int) or 0)
EMBED_KEY = cfg("PROGRESS_EMBED_KEY", "daily_progress", str)
AUTOPIN = bool(cfg("PROGRESS_EMBED_PIN", True, bool))
AUTO_INCREMENT = bool(cfg("NEURO_AUTO_INCREMENT", False, bool))
AUTO_INCREMENT_STEP = float(cfg("NEURO_AUTO_INCREMENT_STEP", 0.25, float))
SMOKE_MODE = bool(cfg("SMOKE_MODE", False, bool))

class ProgressEmbedSolo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.scribe = EmbedScribe(bot)
        self.dupe = DuplicateSuppressor(ttl_seconds=120)
        nmem.ensure_files()
        if not SMOKE_MODE:
            self.update_embed.start()

    def cog_unload(self):
        try: self.update_embed.cancel()
        except Exception: pass

    async def _get_channel(self) -> discord.abc.Messageable:
        if TARGET_CHANNEL_ID:
            ch = self.bot.get_channel(TARGET_CHANNEL_ID) or await self.bot.fetch_channel(TARGET_CHANNEL_ID)
            if ch: return ch
        for g in self.bot.guilds:
            for ch in g.text_channels:
                return ch
        raise RuntimeError("No text channel available for progress embed")

    def _format_embed(self) -> discord.Embed:
        junior = nmem.load_junior()
        overall = float(junior.get("overall", 0.0))
        bar_len = 22
        filled = int(round(overall/100 * bar_len))
        bar = "[" + "—" * filled + " " * (bar_len - filled) + f"] {overall:.1f}%"

        e = discord.Embed(title="Daily Progress", color=discord.Color.blurple())
        e.add_field(name="\u200b", value=f"{bar}", inline=False)
        e.add_field(name="Stickers", value="total sent 0, success 0\nToday sent 0", inline=False)
        e.add_field(name="Slang", value="lexicon 0 (pos 0, neg 0)\nNew today False", inline=False)
        e.add_field(name="7d sent", value="▮▯▯▯▯▯▯", inline=False)
        e.set_footer(text=f"key:{EMBED_KEY} • TK–SD learning • {dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}Z")
        return e

    @tasks.loop(seconds=45)
    async def update_embed(self):
        try:
            if AUTO_INCREMENT:
                nmem.bump_progress("TK", "L1", AUTO_INCREMENT_STEP)
            ch = await self._get_channel()
            embed = self._format_embed()
            payload_sig = f"{embed.title}|{embed.footer.text if embed.footer else ''}|{len(embed.fields)}"
            if self.dupe.should_skip(ch.id, EMBED_KEY, payload_sig):
                return
            await self.scribe.upsert(ch, EMBED_KEY, embed, pin=AUTOPIN)
        except Exception as e:
            print("[progress_embed_solo] update error:", e)

    @update_embed.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(ProgressEmbedSolo(bot))