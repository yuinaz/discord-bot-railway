
try:
    import discord
    from discord.ext import commands
except Exception:  # allow smoke without discord installed
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
import datetime as dt, asyncio, logging
log = logging.getLogger(__name__)

try:
    from satpambot.bot.modules.discord_bot.utils.sticky_embed import StickyEmbed
except Exception:
    StickyEmbed = None
try:
    from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
except Exception:
    UpstashClient = None

class NeuroDailyProgress(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cid = cfg_int("NEURO_LITE_PROGRESS_CHANNEL_ID", 0) or None
        self.tz  = cfg_str("BOT_TZ", "Asia/Jakarta") or "Asia/Jakarta"
        self.H   = int(cfg_int("NEURO_LITE_PROGRESS_TIME_HOUR", 21) or 21)
        self.M   = int(cfg_int("NEURO_LITE_PROGRESS_TIME_MINUTE", 0) or 0)
        self.client = UpstashClient() if UpstashClient else None
        try:
            from discord.ext import tasks  # type: ignore
            self.loop = tasks.loop(minutes=30)(self._loop_impl)
            self.loop.start()
        except Exception:
            pass

    async def _loop_impl(self):
        try: await self._tick()
        except Exception as e: log.warning("[neuro-daily] tick failed: %r", e)

    async def _tick(self):
        if not self.cid: return
        try:
            now = dt.datetime.now(dt.timezone.utc).astimezone(dt.ZoneInfo(self.tz))
        except Exception:
            now = dt.datetime.utcnow()
        if not (now.hour == self.H and abs(now.minute - self.M) < 5): return
        key = f"neuro:daily:{now.date().isoformat()}"
        if self.client and getattr(self.client, "enabled", False):
            try:
                if await self.client.get_raw(key) is not None: return
            except Exception: pass
        ch = self.bot.get_channel(self.cid)
        if ch is None:
            try: ch = await self.bot.fetch_channel(self.cid)
            except Exception: return
        senior = "?"
        try:
            if self.client and getattr(self.client, "enabled", False):
                s = await self.client.get_raw("xp:bot:senior_total_v2")
                if s is not None: senior = str(s)
        except Exception: pass
        body = f"**Daily Progress — {now.strftime('%Y-%m-%d')}**\nXP total senior: {senior}\nCatatan: auto-update."
        if StickyEmbed:
            se = StickyEmbed()
            try:
                msg = await se.ensure(ch, "NEURO-LITE Daily Progress")
                e = discord.Embed(title="NEURO-LITE Daily Progress", description=body)
                e.set_footer(text="NEURO_DAILY_PROGRESS")
                await msg.edit(embed=e, suppress=False)
            except Exception: pass
        else:
            try: await ch.send(body)
            except Exception: pass
        if self.client and getattr(self.client, "enabled", False):
            try: await self.client.setex(key, 60*60*24*40, "1")
            except Exception: pass

async def setup(bot): await bot.add_cog(NeuroDailyProgress(bot))