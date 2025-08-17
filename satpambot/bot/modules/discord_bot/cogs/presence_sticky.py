import datetime as dt
import logging
from typing import Optional

import discord
from discord.ext import commands, tasks

from satpambot.bot.modules.discord_bot.utils import sticky_store

log = logging.getLogger(__name__)

TARGET_CHANNEL_NAME = "log-botphising"
GREEN = 0x3BA55D

def _tz_wib_now():
    return dt.datetime.utcnow() + dt.timedelta(hours=7)

def _format_embed(bot: commands.Bot) -> discord.Embed:
    now = _tz_wib_now()
    stamp = now.strftime("%Y-%m-%d %H:%M:%S") + " WIB (+07:00)"
    e = discord.Embed(
        title="SatpamBot Status",
        description="✅ **SatpamBot** online dan siap berjaga.",
        color=GREEN,
        timestamp=now,
    )
    disc = f"{bot.user}" if bot.user else "bot"
    e.add_field(name="Akun", value=f"**{disc}**", inline=True)
    e.add_field(name="Presence", value="`presence=online`", inline=True)
    e.set_footer(text=f"Terakhir diperbarui: {stamp}")
    return e

def _pick_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    # Strict: ONLY #log-botphising
    ch = discord.utils.get(guild.text_channels, name=TARGET_CHANNEL_NAME)
    if ch:
        sticky_store.upsert_guild(guild.id, channel_id=ch.id)
        return ch
    log.warning("[sticky] Channel #%s tidak ditemukan di guild %s", TARGET_CHANNEL_NAME, guild.id)
    return None

class PresenceSticky(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._loop.start()

    def cog_unload(self):
        self._loop.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        log.info("[sticky] on_ready for %s", self.bot.user)
        await self._update_all_guilds()

    async def _update_all_guilds(self):
        for guild in list(self.bot.guilds):
            try:
                await self._update_guild(guild)
            except Exception as e:
                log.exception("[sticky] gagal update guild %s: %s", guild.id, e)

    async def _update_guild(self, guild: discord.Guild):
        ch = _pick_channel(guild)
        if not ch:
            return
        st = sticky_store.get_guild(guild.id)
        last_edit_ts = float(st.get("last_edit_ts", 0))
        now = dt.datetime.utcnow().timestamp()
        # Edit maksimal setiap 10 menit (anti spam)
        if last_edit_ts and (now - last_edit_ts) < 600:
            return

        embed = _format_embed(self.bot)
        msg_id = st.get("message_id")
        try:
            if msg_id:
                msg = await ch.fetch_message(int(msg_id))
                await msg.edit(content=f"✅ Online sebagai **{self.bot.user}** | `presence=online`", embed=embed)
            else:
                msg = await ch.send(content=f"✅ Online sebagai **{self.bot.user}** | `presence=online`", embed=embed)
                sticky_store.upsert_guild(guild.id, message_id=msg.id)
            sticky_store.upsert_guild(guild.id, channel_id=ch.id, last_edit_ts=now)
        except discord.NotFound:
            msg = await ch.send(content=f"✅ Online sebagai **{self.bot.user}** | `presence=online`", embed=embed)
            sticky_store.upsert_guild(guild.id, channel_id=ch.id, message_id=msg.id, last_edit_ts=now)
        except discord.Forbidden:
            log.warning("[sticky] tidak punya izin edit/kirim di #%s (%s)", getattr(ch, "name", ch.id), ch.id)
        except discord.HTTPException as e:
            log.warning("[sticky] HTTPException saat edit/kirim: %s", e)

    @tasks.loop(minutes=15)
    async def _loop(self):
        await self._update_all_guilds()

    @_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(PresenceSticky(bot))