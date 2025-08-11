import os, time, discord

LOG_CHANNEL_NAME = os.getenv("LOG_CHANNEL_NAME", "log-botphising")
# Force a default ID (can be overridden by env). 0 disables.
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "1400375184048787566"))

_status_msg_cache_by_channel = {}  # (guild_id, channel_id) -> message_id

def _find_log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    if not guild:
        return None
    # Prefer ID for accuracy
    if LOG_CHANNEL_ID:
        ch = guild.get_channel(LOG_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel):
            return ch
    # Fallback by name: accept a few common variants
    names = {LOG_CHANNEL_NAME, "lot-botphising", "log-botphishing"}
    for ch in guild.text_channels:
        if ch.name in names:
            return ch
    return None

async def upsert_status_embed_in_channel(ch: discord.TextChannel, text: str):
    if not ch:
        return False
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    emb = discord.Embed(title="SatpamBot Status", description=text, color=discord.Color.green())
    emb.set_footer(text=f"Terakhir diperbarui: {now}")
    key = (ch.guild.id if ch.guild else 0, ch.id)
    mid = _status_msg_cache_by_channel.get(key)
    msg = None
    if mid:
        try:
            msg = await ch.fetch_message(mid)
        except Exception:
            msg = None
    if msg is None:
        try:
            msg = await ch.send(embed=emb)
            _status_msg_cache_by_channel[key] = msg.id
            return True
        except Exception:
            return False
    else:
        try:
            await msg.edit(embed=emb)
            return True
        except Exception:
            return False

async def upsert_status_embed(guild: discord.Guild, text: str):
    ch = _find_log_channel(guild)
    if not ch:
        return False
    return await upsert_status_embed_in_channel(ch, text)

async def announce_bot_online(guild: discord.Guild, bot_tag: str):
    try:
        await upsert_status_embed(guild, "✅ SatpamBot online dan siap berjaga.")
    except Exception:
        ch = _find_log_channel(guild)
        if ch:
            try: await ch.send("✅ SatpamBot online dan siap berjaga.")
            except Exception: pass
