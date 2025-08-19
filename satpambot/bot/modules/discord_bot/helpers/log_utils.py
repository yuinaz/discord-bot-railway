from __future__ import annotations
import asyncio, logging, os, time, hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import discord
from satpambot.bot.modules.discord_bot.utils import sticky_store

log = logging.getLogger(__name__)

_STATUS_MARKER = "SATPAMBOT_STATUS_V1"
_lock = asyncio.Lock()

def _wib_now() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=7)

def _uptime_human(bot: discord.Client) -> str:
    start = getattr(bot, "start_time", None)
    if not start:
        try:
            start = float(os.getenv("BOT_START_TIME", "0"))
        except Exception:
            start = 0
    if not start:
        return "0s"
    s = max(0, int(time.time() - float(start)))
    # format H:MM:SS or Dd H:MM
    if s < 3600:
        m, sec = divmod(s, 60)
        return f"{m}m {sec}s"
    d, rem = divmod(s, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    return (f"{d}d {h}h {m}m" if d else f"{h}h {m}m")

def _presence_str(bot: discord.Client) -> str:
    try:
        st = bot.status.name  # type: ignore[attr-defined]
    except Exception:
        st = "online"
    return f"presence={st}"

def _embed_and_content(bot: discord.Client) -> Tuple[discord.Embed, str]:
    uptime = _uptime_human(bot)
    pres = _presence_str(bot)
    e = discord.Embed(
        title="SatpamBot Status",
        description=f"Status ringkas bot.",
        colour=0x3BA55D,
        timestamp=_wib_now().astimezone(timezone.utc),
    )
    e.add_field(name="Akun", value=str(bot.user), inline=False)
    e.add_field(name="Presence", value=f"`{pres}`", inline=True)
    e.add_field(name="Uptime", value=f"`{uptime}`", inline=True)
    e.set_footer(text=_STATUS_MARKER)
    content = f"✅ Online sebagai **{bot.user}** | `{pres}` | `uptime={uptime}`"
    return e, content

async def _find_channel_by_id_or_name(bot: discord.Client, guild: discord.Guild) -> Optional[discord.TextChannel]:
    # Resolve by env first
    ch_id = 0
    for key in ("STATUS_CHANNEL_ID", "LOG_CHANNEL_ID"):
        try:
            ch_id = int(os.getenv(key, "0") or 0)
            if ch_id:
                break
        except Exception:
            ch_id = 0
    ch = guild.get_channel(ch_id) if ch_id else None
    if isinstance(ch, discord.TextChannel):
        return ch
    # Fallback by names
    names = [os.getenv("STATUS_CHANNEL_NAME",""), os.getenv("LOG_CHANNEL_NAME",""), "log-botphising", "general"]
    for nm in names:
        nm = (nm or "").strip()
        if not nm: continue
        cand = discord.utils.get(guild.text_channels, name=nm)
        if isinstance(cand, discord.TextChannel):
            return cand
    return None

async def _get_or_create_message(bot: discord.Client, ch: discord.TextChannel, guild_id: int):
    rec = sticky_store.get_guild(guild_id) or {}
    msg_id = rec.get("message_id")
    msg = None
    if msg_id:
        try:
            msg = await ch.fetch_message(int(msg_id))
        except Exception:
            msg = None
    if msg is None:
        try:
            e, content = _embed_and_content(bot)
            msg = await ch.send(content=content, embed=e)
            sticky_store.upsert_guild(guild_id, channel_id=ch.id, message_id=msg.id, last_edit_ts=int(time.time()))
        except Exception as e:
            log.warning("[status] create message failed in #%s: %s", getattr(ch, "name", "?"), e)
            return None
    return msg

async def upsert_status_embed_in_channel(bot: discord.Client, ch: discord.TextChannel):
    MIN_INTERVAL = 3600  # 1 hour; hardcoded
    try:
        guild = ch.guild
        rec = sticky_store.get_guild(guild.id) or {}
        last_ts = int(rec.get("last_edit_ts") or 0)
        now = int(time.time())
        e, content = _embed_and_content(bot)
        # hash to detect meaningful change
        h = hashlib.sha256((content + str(e.to_dict())).encode("utf-8", "ignore")).hexdigest()
        last_hash = rec.get("last_hash")

        if (now - last_ts) < MIN_INTERVAL and last_hash == h:
            # Skip spam
            return

        async with _lock:
            msg = await _get_or_create_message(bot, ch, guild.id)
            if not msg:
                return
            try:
                await msg.edit(content=content, embed=e)
            except Exception as ex:
                log.debug("[status] edit failed, try send new: %s", ex)
                msg = await ch.send(content=content, embed=e)
            sticky_store.upsert_guild(
                guild.id,
                channel_id=ch.id,
                message_id=getattr(msg, "id", None),
                last_edit_ts=now,
                last_hash=h,
            )
    except discord.Forbidden:
        log.warning("[status] no permission to send/edit in #%s", getattr(ch, "name", "?"))
    except Exception as e:
        log.warning("[status] upsert error: %s", e)

async def upsert_status_embed(bot: discord.Client, guild: discord.Guild):
    ch = await _find_channel_by_id_or_name(bot, guild)
    if ch:
        await upsert_status_embed_in_channel(bot, ch)
