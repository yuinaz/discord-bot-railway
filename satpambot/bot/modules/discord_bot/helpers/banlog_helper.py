import os, logging, discord

log = logging.getLogger(__name__)

TARGET_CHANNEL_NAME = os.getenv("BAN_LOG_CHANNEL_NAME", "log-botphising")
TARGET_THREAD_NAME  = os.getenv("BAN_LOG_THREAD_NAME", "Ban Log")

async def get_banlog_thread(guild: discord.Guild) -> discord.Thread | discord.TextChannel | None:
    # Priority: explicit ID -> name
    try:
        ch_id = int(os.getenv("BAN_LOG_CHANNEL_ID", "0"))
    except Exception:
        ch_id = 0
    ch = None
    if ch_id:
        ch = guild.get_channel(ch_id)
    if not isinstance(ch, discord.TextChannel):
        ch = discord.utils.get(guild.text_channels, name=TARGET_CHANNEL_NAME)
    if not isinstance(ch, discord.TextChannel):
        log.warning("[banlog] TextChannel not found (id=%s, name=%s)", ch_id, TARGET_CHANNEL_NAME)
        return None
    # Find active thread by name (property, not coroutine)
    try:
        active = list(getattr(ch, "threads", []) or [])
    except Exception:
        active = []
    for th in active:
        try:
            if isinstance(th, discord.Thread) and th.name == TARGET_THREAD_NAME:
                return th
        except Exception:
            continue
    # Create if not exists; if creation fails, fall back to channel
    try:
        th = await ch.create_thread(name=TARGET_THREAD_NAME, type=discord.ChannelType.public_thread)
        return th
    except Exception as e:
        log.warning("[banlog] create_thread failed: %s (fallback=channel)", e)
        return ch
