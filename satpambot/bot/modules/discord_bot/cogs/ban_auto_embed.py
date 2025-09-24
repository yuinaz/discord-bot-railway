
from __future__ import annotations
import asyncio, os, time
import discord
from discord.ext import commands

def _get_int_env(name: str, default: int) -> int:
    try: return int(os.getenv(name, str(default)).strip())
    except Exception: return default

LOG_CHANNEL_ID = _get_int_env("LOG_CHANNEL_ID", _get_int_env("LOG_CHANNEL_ID_RAW", 0))
WAIT_BEFORE_CHECK_MS = 800
_DEDUP_SEC = 5
_recent_bans = {}

async def _get_log_target(guild: discord.Guild):
    if not LOG_CHANNEL_ID: return None
    ch = guild.get_channel(LOG_CHANNEL_ID)
    if isinstance(ch, discord.Thread): return ch
    if isinstance(ch, discord.TextChannel):
        try:
            for t in ch.threads:
                if not t.archived and "ban log" in t.name.lower(): return t
        except Exception: pass
        return ch
    return None

def _embed_log_simple(user: discord.abc.User):
    tag = f"{user.name} ({user.id})"
    return discord.Embed(title="Banned", description=tag, color=discord.Color.dark_grey())

class BanAutoEmbed(commands.Cog):
    def __init__(self, bot: commands.Bot): self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        now = time.time()
        last = _recent_bans.get(user.id, 0)
        if now - last < _DEDUP_SEC:
            return
        _recent_bans[user.id] = now

        await asyncio.sleep(WAIT_BEFORE_CHECK_MS / 1000)
        target = await _get_log_target(guild)
        if target and isinstance(target, (discord.TextChannel, discord.Thread)):
            try: await target.send(embed=_embed_log_simple(user))
            except Exception: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(BanAutoEmbed(bot))
