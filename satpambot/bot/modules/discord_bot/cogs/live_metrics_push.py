
import datetime as dt, platform, psutil
import discord
from discord.ext import tasks, commands
from satpambot.config.compat_conf import get_conf
from satpambot.bot.utils import embed_scribe

def _uptime_str(start):
    delta = dt.datetime.utcnow() - start
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, _ = divmod(rem, 60)
    return f"{h}h {m}m"

class LiveMetricsPush(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conf = get_conf()
        self.channel_id = int(self.conf.get("PHISH_LOG_CHANNEL_ID", 0)) or int(self.conf.get("PROGRESS_EMBED_CHANNEL_ID", 0))
        self.key = "SATPAMBOT_STATUS_V1"
        self.started = dt.datetime.utcnow()
        self.task.start()

    def cog_unload(self):
        self.task.cancel()

    @tasks.loop(minutes=18)
    async def task(self):
        ch = self.bot.get_channel(self.channel_id)
        if not ch:
            return
        pres = "presence=online"  # best-effort
        uptime = _uptime_str(self.started)
        e = discord.Embed(title="SatpamBot Status", description="Status ringkas bot.", color=0x2ecc71)
        e.add_field(name="Akun", value=str(getattr(self.bot.user,'name','?')) + "#" + str(getattr(self.bot.user,'discriminator','0000')), inline=False)
        e.add_field(name="Presence", value=pres, inline=True)
        e.add_field(name="Uptime", value=uptime, inline=True)
        e.set_footer(text=self.key)
        await embed_scribe.upsert(ch, self.key, e, pin=False)

    @task.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(LiveMetricsPush(bot))
