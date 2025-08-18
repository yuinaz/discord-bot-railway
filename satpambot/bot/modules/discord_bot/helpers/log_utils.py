from __future__ import annotations
import asyncio, logging, os
from datetime import datetime, timezone, timedelta
from typing import Optional
import discord
from satpambot.bot.modules.discord_bot.utils import sticky_store
log = logging.getLogger(__name__)
_STATUS_MARKER = "SATPAMBOT_STATUS_V1"
_lock = asyncio.Lock()
def _wib_now(): return datetime.now(timezone.utc) + timedelta(hours=7)
def _format_embed(bot: discord.Client) -> discord.Embed:
    e = discord.Embed(title="SatpamBot Status", description="SatpamBot online dan siap berjaga.", colour=0x3BA55D, timestamp=_wib_now().astimezone(timezone.utc))
    e.add_field(name="Akun", value=str(bot.user), inline=False)
    e.add_field(name="Presence", value="`presence=online`", inline=False)
    e.set_footer(text=_STATUS_MARKER); return e
async def _find_channel_by_id_or_name(bot: discord.Client, guild: discord.Guild) -> Optional[discord.TextChannel]:
    try: ch_id = int(os.getenv("LOG_CHANNEL_ID","0") or "0")
    except Exception: ch_id = 0
    if ch_id:
        try:
            ch = bot.get_channel(ch_id) or await bot.fetch_channel(ch_id)
            if isinstance(ch, (discord.TextChannel, discord.Thread)): return ch
        except Exception: pass
    target_name = (os.getenv("LOG_CHANNEL_NAME") or "log-botphising").strip()
    for ch in getattr(guild, "text_channels", []):
        try:
            if getattr(ch, "name", None) == target_name and (perms := ch.permissions_for(guild.me)) and perms.send_messages: return ch
        except Exception: continue
    for ch in getattr(guild, "text_channels", []):
        try:
            perms = ch.permissions_for(guild.me)
            if perms and perms.send_messages: return ch
        except Exception: continue
    return None
async def upsert_status_embed_in_channel(bot: discord.Client, ch: discord.abc.Messageable):
    async with _lock:
        try:
            guild = getattr(ch, "guild", None) or (bot.guilds[0] if getattr(bot, "guilds", None) else None)
            if guild is None: return
            st = sticky_store.get_guild(guild.id); msg_id = st.get("message_id"); embed = _format_embed(bot)
            msg = None
            if msg_id:
                try: msg = await ch.fetch_message(int(msg_id))
                except Exception: msg=None
            if msg is None:
                try:
                    async for m in ch.history(limit=50):
                        if m.author.id == bot.user.id and m.embeds:
                            for e in m.embeds:
                                if (e.footer and e.footer.text == _STATUS_MARKER) or (e.title == "SatpamBot Status"):
                                    msg = m; break
                        if msg: break
                except Exception: msg=None
            content = f"✅ Online sebagai **{bot.user}** | `presence=online`"
            if msg is not None:
                try: await msg.edit(content=content, embed=embed)
                except Exception: msg = await ch.send(content=content, embed=embed)
            else:
                msg = await ch.send(content=content, embed=embed)
            try: sticky_store.upsert_guild(guild.id, channel_id=getattr(ch, "id", None), message_id=getattr(msg, "id", None), last_edit_ts=int(datetime.utcnow().timestamp()))
            except Exception: pass
        except discord.Forbidden: log.warning("[status] tidak punya izin untuk kirim/edit di #%s", getattr(ch, "name", ch))
        except Exception as e: log.warning("[status] upsert error: %s", e)
async def upsert_status_embed(bot: discord.Client, guild: discord.Guild):
    ch = await _find_channel_by_id_or_name(bot, guild)
    if ch: await upsert_status_embed_in_channel(bot, ch)
