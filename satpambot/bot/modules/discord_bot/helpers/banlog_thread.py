
import discord
from . import static_cfg

BAN_THREAD_NAME = "Ban Log"

def _log_channel_name():
    return getattr(static_cfg, "LOG_CHANNEL_NAME", "log-botphising")

async def get_log_channel(guild: "discord.Guild"):
    name = (_log_channel_name() or "").lower()
    if not name:
        return guild.system_channel
    ch = discord.utils.get(guild.text_channels, name=name)
    return ch or guild.system_channel

async def ensure_ban_thread(guild_or_channel):
    """Return a thread named 'Ban Log' under log channel; create if missing.
    Accepts guild or channel.
    """
    # resolve channel
    if hasattr(guild_or_channel, "send"):
        channel = guild_or_channel
    else:
        channel = await get_log_channel(guild_or_channel)
    if channel is None:
        return None

    # search existing
    try:
        for th in getattr(channel, "threads", []):
            if (getattr(th, "name", "") or "").lower() == BAN_THREAD_NAME.lower():
                return th
    except Exception:
        pass

    # create
    try:
        th = await channel.create_thread(name=BAN_THREAD_NAME, auto_archive_duration=10080)  # 7d
        return th
    except Exception:
        return channel
