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


# ===== Error log rolling embed (auto-update) =====
import os as _os, json as _json, time as _time, traceback as _traceback
from pathlib import Path as _Path

_ERROR_STATE_FILE = _Path("data/errorlog_state.json")
_MAX_ENTRIES = 10
_EMBED_TITLE = "❌ Error Log (Auto-Update)"

def _load_state():
    try:
        if _ERROR_STATE_FILE.exists():
            return _json.loads(_ERROR_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _save_state(state):
    try:
        _ERROR_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ERROR_STATE_FILE.write_text(_json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

async def _get_error_channel(guild):
    if guild is None:
        return None
    ch_id = _os.getenv("ERROR_LOG_CHANNEL_ID")
    ch = None
    if ch_id and ch_id.isdigit():
        ch = guild.get_channel(int(ch_id))
        if ch:
            return ch
    for name in ("errorlog-bot", "log-satpam-error", "log-satpam-chat", "mod-command"):
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch:
            return ch
    return None

async def _get_or_create_error_message(channel):
    state = _load_state()
    gkey = str(channel.guild.id)
    gstate = state.get(gkey, {})
    msg_id = gstate.get("message_id")
    if msg_id:
        try:
            m = await channel.fetch_message(int(msg_id))
            return m, state
        except Exception:
            pass
    try:
        async for m in channel.history(limit=50):
            if m.author == channel.guild.me and m.embeds:
                if m.embeds[0].title == _EMBED_TITLE:
                    gstate["message_id"] = m.id
                    state[gkey] = gstate
                    _save_state(state)
                    return m, state
    except Exception:
        pass
    emb = discord.Embed(title=_EMBED_TITLE, description="(no errors yet)")
    try:
        m = await channel.send(embed=emb)
        gstate["message_id"] = m.id
        gstate["entries"] = []
        state[gkey] = gstate
        _save_state(state)
        return m, state
    except Exception:
        return None, state

def _format_entries(entries):
    if not entries:
        return "(no errors yet)"
    text = "\n".join(entries[-_MAX_ENTRIES:])
    if len(text) > 3800:
        text = text[-3800:]
    return text

async def upsert_errorlog_embed(guild, entry: str):
    ch = await _get_error_channel(guild)
    if not ch:
        return
    msg, state = await _get_or_create_error_message(ch)
    if not msg:
        return
    gkey = str(guild.id)
    gstate = state.get(gkey, {"entries": []})
    entries = gstate.get("entries", [])
    entries.append(entry)
    if len(entries) > _MAX_ENTRIES:
        entries = entries[-_MAX_ENTRIES:]
    gstate["entries"] = entries
    state[gkey] = gstate
    _save_state(state)
    emb = discord.Embed(title=_EMBED_TITLE, description=_format_entries(entries))
    try:
        await msg.edit(embed=emb)
    except Exception:
        pass

async def send_error_log(guild, title: str, err: Exception, extra: dict | None = None):
    ts = _time.strftime("%Y-%m-%d %H:%M:%S")
    base = f"• **{ts}** — **{title}** — `{type(err).__name__}: {err}`"
    if extra:
        kv = " | ".join(f"{k}:{str(v)[:60]}" for k, v in extra.items())
        base = f"{base} — {kv}"
    await upsert_errorlog_embed(guild, base)


# ===== Single updatable STATUS embed (online + heartbeat) =====
import json as _json, os as _os, time as _time
_STATUS_STATE_FILE = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))), "data", "status_embed.json")

def _status_load():
    try:
        _os.makedirs(_os.path.dirname(_STATUS_STATE_FILE), exist_ok=True)
        with open(_STATUS_STATE_FILE, "r", encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {}

def _status_save(state: dict):
    try:
        _os.makedirs(_os.path.dirname(_STATUS_STATE_FILE), exist_ok=True)
        with open(_STATUS_STATE_FILE, "w", encoding="utf-8") as f:
            _json.dump(state, f)
    except Exception:
        pass

async def upsert_status_embed(guild: discord.Guild, text: str, channel_name: str = LOG_PHISH_NAME):
    """Create or update a single status embed in the given guild's log channel."""
    if not guild: 
        return
    ch = find_text_channel(guild, channel_name)
    if not ch:
        return
    state = _status_load()
    key = str(guild.id)
    now = _time.strftime("%Y-%m-%d %H:%M:%S UTC", _time.gmtime())
    emb = discord.Embed(title="SatpamBot Status", description=text, color=discord.Color.green())
    emb.set_footer(text=f"Terakhir diperbarui: {now}")
    msg_id = state.get(key)
    msg = None
    if msg_id:
        try:
            msg = await ch.fetch_message(int(msg_id))
        except Exception:
            msg = None
    if msg is None:
        try:
            msg = await ch.send(embed=emb)
            state[key] = str(msg.id)
            _status_save(state)
        except Exception:
            return
    else:
        try:
            await msg.edit(embed=emb)
        except Exception:
            pass
