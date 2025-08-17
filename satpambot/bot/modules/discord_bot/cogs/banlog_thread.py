from __future__ import annotations
import os, datetime, json
import discord
from discord.ext import commands

async def _get_log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    # env id wins
    try:
        ch_id = int(os.getenv("BAN_LOG_CHANNEL_ID","0"))
    except Exception:
        ch_id = 0
    if ch_id:
        ch = guild.get_channel(ch_id)
        if isinstance(ch, discord.TextChannel):
            return ch
    # fallback by name
    for name in ("log-botphising","log-botphishing","bot-log","logs"):
        for ch in guild.text_channels:
            if ch.name == name:
                return ch
    return None


def _append_recent_ban(user, guild):
    try:
        import json, os, time
        path = os.path.join("data","recent_bans.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {"items":[]}
        if os.path.exists(path):
            try:
                data = json.load(open(path,"r",encoding="utf-8"))
            except Exception:
                data = {"items":[]}
        item = {
            "key": f"{getattr(guild,'id',0)}-{getattr(user,'id',user)}-{int(time.time())}",
            "ts": int(time.time()),
            "user_id": getattr(user,'id',user),
            "user_name": getattr(user,'name', str(user)),
            "guild_id": getattr(guild,'id',0),
            "guild_name": getattr(guild,'name',''),
        }
        data["items"] = (data.get("items",[]) + [item])[-100:]
        json.dump(data, open(path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass

class BanLogThread(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
async def on_member_ban(self, guild: discord.Guild, user: discord.User):
    ch = await _get_log_channel(guild)
    if not ch:
        return
    # Use (or create once) a single thread named from config
    try:
        cfg = json.load(open("data/phish_config.json","r",encoding="utf-8"))
    except Exception:
        cfg = {"log_thread_name":"Ban Log"}
    thread_name = cfg.get("log_thread_name","Ban Log")
    # find existing thread
    target_thread = None
    try:
        async for th in ch.threads(limit=50):
            if th.name == thread_name:
                target_thread = th; break
    except Exception:
        pass
    if not target_thread:
        try:
            target_thread = await ch.create_thread(
                name=thread_name, auto_archive_duration=1440, type=discord.ChannelType.public_thread
            )
        except Exception:
            target_thread = None
    emb = discord.Embed(title="Banned", description=f"{user} (`{getattr(user,'id',user)}`)")
    try:
        if target_thread:
            await target_thread.send(embed=emb)
        _append_recent_ban(user, guild)
        else:
            await ch.send(embed=emb)
            _append_recent_ban(user, guild)
    except Exception:
        pass

async def setup(bot): await bot.add_cog(BanLogThread(bot))