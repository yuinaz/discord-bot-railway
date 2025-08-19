import os, logging, discord
log = logging.getLogger(__name__)

TARGET_CHANNEL_NAME = os.getenv("BAN_LOG_CHANNEL_NAME", os.getenv("LOG_CHANNEL_NAME","log-botphising"))
TARGET_THREAD_NAME  = os.getenv("BAN_LOG_THREAD_NAME", "Ban Log")

async def _resolve_channel(guild: discord.Guild) -> discord.TextChannel | None:
    ch_id = 0
    for key in ("BAN_LOG_CHANNEL_ID","LOG_CHANNEL_ID"):
        try:
            ch_id = int(os.getenv(key, "0") or 0)
            if ch_id:
                break
        except Exception:
            ch_id = 0
    ch = guild.get_channel(ch_id) if ch_id else None
    if not isinstance(ch, discord.TextChannel) and TARGET_CHANNEL_NAME:
        ch = discord.utils.get(guild.text_channels, name=TARGET_CHANNEL_NAME)
    if not isinstance(ch, discord.TextChannel):
        log.warning("[banlog] TextChannel not found (id=%s, name=%s)", ch_id, TARGET_CHANNEL_NAME)
        return None
    perms = ch.permissions_for(guild.me)
    if not (perms and (perms.send_messages or perms.create_public_threads)):
        log.warning("[banlog] Bot lacks permission to log in #%s", getattr(ch, 'name', '?'))
    return ch

async def _find_existing_thread(ch: discord.TextChannel) -> discord.Thread | None:
    try:
        for th in list(getattr(ch, 'threads', [])) or []:
            if isinstance(th, discord.Thread) and th.name == TARGET_THREAD_NAME:
                return th
    except Exception:
        pass
    # Try archived threads
    try:
        async for th in ch.archived_threads(limit=50):
            if th.name == TARGET_THREAD_NAME:
                if th.archived:
                    try:
                        await th.edit(archived=False, locked=False)
                    except Exception:
                        pass
                return th
    except Exception as e:
        log.debug("[banlog] archived_threads fetch failed: %s", e)
    return None

async def get_banlog_thread(guild: discord.Guild) -> discord.Thread | discord.TextChannel | None:
    ch = await _resolve_channel(guild)
    if not isinstance(ch, discord.TextChannel):
        return None
    th = await _find_existing_thread(ch)
    if th:
        return th
    # Create a new thread if possible
    try:
        th = await ch.create_thread(name=TARGET_THREAD_NAME, type=discord.ChannelType.public_thread, auto_archive_duration=10080)
        return th
    except Exception as e:
        log.warning("[banlog] create_thread failed: %s (fallback=channel)", e)
        return ch
