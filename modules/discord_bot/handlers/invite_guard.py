from modules.discord_bot.helpers.banlog import record_ban_and_log
# NSFW invite guard (auto)
import os, re, logging, discord
from modules.discord_bot.helpers.permissions import is_exempt_user, is_whitelisted_channel  # permissions import
from modules.discord_bot.helpers.db import log_action
from modules.discord_bot.helpers.log_utils import send_ban_embeds

INVITE_RE = re.compile(r"(?:https?://)?(?:discord(?:app)?\.com/invite|discord\.gg)/([A-Za-z0-9-]+)", re.IGNORECASE)
from modules.discord_bot.helpers.config_manager import get_flag
AUTOBAN = str(get_flag("NSFW_INVITE_AUTOBAN","true")).lower()=="true"

async def check_nsfw_invites(message: discord.Message, bot: discord.Client):
    if is_whitelisted_channel(getattr(message,'channel',None)) or is_exempt_user(getattr(message,'author',None)): return
    if not AUTOBAN or message.author.bot:
        return
    content = message.content or ""
    m = INVITE_RE.search(content)
    if not m:
        return
    code = m.group(1)
    try:
        invite = await bot.fetch_invite(code)
        g = getattr(invite, "guild", None)
        if not g:
            return
        nsfw_level = getattr(g, "nsfw_level", None)
        is_nsfw = False
        if hasattr(g, "nsfw"):
            is_nsfw = bool(getattr(g, "nsfw"))
        elif nsfw_level is not None:
            val = getattr(nsfw_level, "value", nsfw_level)
            try:
                is_nsfw = (str(val).lower() not in ("0","none","default","safe"))
            except Exception:
                is_nsfw = True
        if is_nsfw and message.guild and g.id != message.guild.id:
            perms = message.guild.me.guild_permissions if message.guild and message.guild.me else None
            if perms and perms.ban_members:
                try:
                    try:
                    await message.delete()
                except Exception:
                    pass
                except Exception:
                    pass
                reason = "Auto-ban: menyebarkan undangan ke server NSFW (guild: " + str(getattr(g,'name','unknown')) + ")"
                try:
                    await message.guild.ban(message.author, reason=reason, delete_message_days=0)
                    await send_ban_embeds(message.guild, message.author, reason)
                except Exception as e:
                    logging.warning("[InviteGuard] Gagal ban: %s", e)
            else:
                logging.info("[InviteGuard] Bot tidak punya permission ban_members")
    except Exception as e:
        logging.warning("[InviteGuard] Error cek undangan: %s", e)
