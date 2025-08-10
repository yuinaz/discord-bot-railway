# log_utils (auto)
import logging, discord

NGOBROL_NAME = "#💬︲ngobrol discord".lstrip("#")
LOG_PHISH_NAME = "log-botphising"
LOG_SATPAM_NAME = "log-satpam-chat"
MOD_CMD_NAME = "mod-command"

def find_text_channel(guild: discord.Guild, name: str):
    if not guild: return None
    name_clean = name.lstrip("#").strip()
    for ch in guild.text_channels:
        if ch.name == name_clean: return ch
    for ch in guild.text_channels:
        if ch.name.lower() == name_clean.lower(): return ch
    return None

def find_sticker_by_name(guild: discord.Guild, name: str):
    try:
        for st in getattr(guild, "stickers", []) or []:
            if getattr(st, "name", "").lower() == name.lower(): return st
    except Exception as e:
        logging.debug("[log_utils] sticker lookup fail: %s", e)
    return None

async def send_ban_embeds(guild: discord.Guild, user: discord.abc.User, reason: str):
    if not guild: return
    import datetime
    emb = discord.Embed(title="🚫 Pengguna diban",
                        description=f"{user.mention} diban otomatis.",
                        color=discord.Color.red(),
                        timestamp=datetime.datetime.utcnow())
    emb.add_field(name="Alasan", value=reason or "-", inline=False)
    try:
        emb.set_author(name=str(user), icon_url=getattr(user.display_avatar, 'url', discord.Embed.Empty))
    except Exception:
        pass

    ch_ngobrol = find_text_channel(guild, "#💬︲ngobrol discord")
    ch_satpam = find_text_channel(guild, LOG_SATPAM_NAME)
    if ch_ngobrol:
        try:
            await ch_ngobrol.send(embed=emb)
            st = find_sticker_by_name(guild, "FibiLaugh")
            if st:
                try: await ch_ngobrol.send(stickers=[st])
                except Exception: pass
        except Exception as e:
            logging.warning("[log_utils] gagal kirim ke ngobrol: %s", e)
    if ch_satpam:
        try: await ch_satpam.send(embed=emb)
        except Exception: pass
    try:
        await update_mod_command_ban_log(guild, user, reason)
    except Exception:
        pass

async def announce_bot_online(guild: discord.Guild, bot_name: str):
    ch = find_text_channel(guild, LOG_PHISH_NAME)
    if not ch: return
    try: await ch.send(f"🟢 Bot aktif sebagai **{bot_name}**")
    except Exception: pass

# Upsert single embed in #mod-command
BAN_LOG_ANCHOR = "[BAN_LOG_ANCHOR]"
MAX_LOG_LINES = 50
def _format_entry(user: discord.abc.User, reason: str):
    tag = getattr(user, "name", "unknown")
    disc = getattr(user, "discriminator", None)
    user_display = f"{tag}#{disc}" if disc not in (None, "0") else tag
    uid = getattr(user, "id", 0)
    reason = (reason or "-").strip()[:200]
    from datetime import datetime
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    return f"- **{user_display}** (`{uid}`) — {reason} — `{ts} UTC`"

def _parse_lines_from_embed(msg: discord.Message):
    try:
        if not msg.embeds: return []
        desc = msg.embeds[0].description or ""
        return [ln.strip() for ln in desc.split("\n") if ln.strip().startswith("- ")]
    except Exception:
        return []

async def _find_or_create_banlog_message(ch: discord.TextChannel) -> discord.Message:
    try:
        async for m in ch.history(limit=50, oldest_first=False):
            if m.author == ch.guild.me and (BAN_LOG_ANCHOR in (m.content or "") or (m.embeds and (m.embeds[0].title or "").lower().startswith("ban log"))):
                return m
    except Exception:
        pass
    emb = discord.Embed(title="Ban Log (Auto-Update)", description="(kosong)", color=discord.Color.orange())
    return await ch.send(BAN_LOG_ANCHOR, embed=emb)

async def update_mod_command_ban_log(guild: discord.Guild, user: discord.abc.User, reason: str):
    ch = find_text_channel(guild, MOD_CMD_NAME)
    if not ch: return
    msg = await _find_or_create_banlog_message(ch)
    lines = _parse_lines_from_embed(msg)
    lines.append(_format_entry(user, reason))
    lines = lines[-MAX_LOG_LINES:]
    emb = discord.Embed(title="Ban Log (Auto-Update)", description="\n".join(lines), color=discord.Color.orange())
    try:
        await msg.edit(content=BAN_LOG_ANCHOR, embed=emb)
    except Exception:
        await ch.send(BAN_LOG_ANCHOR, embed=emb)
