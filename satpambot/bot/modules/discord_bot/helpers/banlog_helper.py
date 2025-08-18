import discord
import logging

log = logging.getLogger(__name__)

TARGET_CHANNEL_NAME = "log-botphising"
TARGET_THREAD_NAME  = "Ban Log"

async def get_banlog_thread(guild: discord.Guild) -> discord.Thread | None:
    ch = discord.utils.get(guild.text_channels, name=TARGET_CHANNEL_NAME)
    if not ch:
        log.warning("[banlog] Channel #%s not found in guild %s", TARGET_CHANNEL_NAME, guild.id)
        return None
    # find existing thread
    try:
        threads = await ch.threads()
    except Exception:
        # Fallback: iterate guild.threads
        threads = getattr(ch, "threads", [])
    for th in threads:
        if isinstance(th, discord.Thread) and (th.name == TARGET_THREAD_NAME):
            return th
    # create if not exists
    try:
        th = await ch.create_thread(name=TARGET_THREAD_NAME, type=discord.ChannelType.public_thread)
        return th
    except Exception as e:
        log.warning("[banlog] failed to create thread: %s", e)
        return None