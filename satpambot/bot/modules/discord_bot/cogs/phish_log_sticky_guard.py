try:
    import discord
    from discord.ext import commands
except Exception:  # allow smoke import without discord installed
    class discord:  # type: ignore
        class Message: ...
    class commands:  # type: ignore
        class Cog:
            @staticmethod
            def listener(*args, **kwargs):
                def _wrap(fn): return fn
                return _wrap
        @staticmethod
        def listener(*args, **kwargs):
            def _wrap(fn): return fn
            return _wrap

from .....config.auto_defaults import cfg_int, cfg_str
import asyncio, logging
log = logging.getLogger(__name__)

try:
    from satpambot.bot.modules.discord_bot.utils.sticky_embed import StickyEmbed
except Exception:
    StickyEmbed = None

class PhishLogStickyGuard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cid = cfg_int("LOG_BOTPHISHING_CHANNEL_ID", 0) or None
        self.title = cfg_str("LOG_BOTPHISHING_STICKY_TITLE", "Leina — Bot Phishing Log") or ""
        self.body  = cfg_str("LOG_BOTPHISHING_STICKY_TEXT", "📌 Referensi pHash & catatan operasi.") or ""
        self._task = None

    @commands.Cog.listener()
    async def on_ready(self):
        if self._task: return
        self._task = asyncio.create_task(self._run())

    async def _run(self):
        await asyncio.sleep(5)
        if not self.cid: return
        ch = self.bot.get_channel(self.cid)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(self.cid)
            except Exception:
                return
        if StickyEmbed is None:
            log.info("[sticky] StickyEmbed util missing; skip"); return
        se = StickyEmbed()
        msg = await se.ensure(ch, self.title)
        FOOTER_MARK = "LEINA_LOG_STICKY"
        try:
            keep_id = msg.id
            # tolerate both async-iterator and coroutine returns
            ait = ch.history(limit=50, oldest_first=False)
            if asyncio.iscoroutine(ait):
                ait = await ait
            async for m in ait:
                if m.id == keep_id: continue
                if m.author.id != getattr(self.bot.user, "id", None): continue
                if not m.embeds: continue
                ft = (getattr(getattr(m.embeds[0], "footer", None), "text", None) or "")
                if FOOTER_MARK in ft:
                    try:
                        await m.delete()
                        await asyncio.sleep(0.2)
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            embed = discord.Embed(title=self.title, description=self.body)
            embed.set_footer(text="LEINA_LOG_STICKY")
            await msg.edit(embed=embed, suppress=False)
            try:
                if not getattr(msg, "pinned", False):
                    await msg.pin(reason="auto-pin log-botphising sticky")
            except Exception:
                pass
        except Exception as e:
            log.warning("[sticky] update failed: %r", e)

async def setup(bot): await bot.add_cog(PhishLogStickyGuard(bot))
