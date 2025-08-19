from __future__ import annotations
import logging, os
from typing import Optional
import discord

log = logging.getLogger(__name__)

def _to_int(x:str)->int:
    try: return int((x or '').strip())
    except Exception: return 0

def _resolve_error_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    cid = _to_int(os.getenv("ERROR_LOG_CHANNEL_ID",""))
    if cid:
        ch = guild.get_channel(cid)
        if isinstance(ch, discord.TextChannel): return ch
    name = (os.getenv("ERROR_LOG_CHANNEL_NAME","errorlog-bot") or "").strip() or "errorlog-bot"
    cand = discord.utils.get(guild.text_channels, name=name)
    if isinstance(cand, discord.TextChannel): return cand
    return None

async def log_error_embed(guild: discord.Guild, title: str, desc: str):
    ch = _resolve_error_channel(guild)
    if not isinstance(ch, discord.TextChannel):
        log.warning("[errorlog] cannot find error log channel in guild %s", getattr(guild,'name','?'))
        return False
    try:
        emb = discord.Embed(title=title, description=desc, color=0xED4245)
        await ch.send(embed=emb)
        return True
    except Exception as e:
        log.warning("[errorlog] send failed: %s", e)
        return False
