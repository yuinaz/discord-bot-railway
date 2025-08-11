
from modules.discord_bot.helpers.banlog import record_ban_and_log
# NSFW invite guard (auto, hardened)
import os, re, logging, discord
from modules.discord_bot.helpers.permissions import is_exempt_user, is_whitelisted_channel
from modules.discord_bot.helpers.log_utils import send_ban_embeds, send_error_log
from modules.discord_bot.helpers.config_manager import get_flag

# Robust pattern for discord.gg / discord.com / discordapp.com invites (with or without scheme)
INVITE_RE = re.compile(r'(?:https?://)?(?:discord(?:app)?\.com/invite|discord\.gg)/([A-Za-z0-9-]+)', re.IGNORECASE)

NSFW_HINTS = [ "sex", "sexcam", "nsfw", "18+", "onlyfans", "nudes", "lewd", "porn", "hentai", "xxx" ]
AUTOBAN = str(get_flag("NSFW_INVITE_AUTOBAN","true")).lower()=="true"

async def check_nsfw_invites(message: discord.Message, bot: discord.Client):
    try:
        if getattr(message.author, "bot", False):
            return
        if is_whitelisted_channel(getattr(message,'channel',None)) or is_exempt_user(getattr(message,'author',None)):
            return
        if not AUTOBAN:
            return
        content = (message.content or "").strip()

        m = INVITE_RE.search(content)
        code = m.group(1) if m else None

        is_nsfw_target = False
        target_name = "unknown"

        if code:
            try:
                invite = await bot.fetch_invite(code, with_counts=False)
                g = getattr(invite, "guild", None)
                target_name = getattr(g, "name", "unknown")
                nsfw_level = getattr(g, "nsfw_level", None)
                if nsfw_level is not None:
                    val = getattr(nsfw_level, "value", nsfw_level)
                    is_nsfw_target = str(val).lower() not in ("0","none","default","safe")
                if not is_nsfw_target and hasattr(g, "nsfw"):
                    is_nsfw_target = bool(getattr(g, "nsfw"))
            except Exception as e:
                logging.debug("[InviteGuard] fetch_invite error: %s", e)

        mass_mention = ("@everyone" in content) or ("@here" in content)
        nsfw_words = any(w in content.lower() for w in NSFW_HINTS)

        should_ban = bool(is_nsfw_target or (code and nsfw_words) or (mass_mention and nsfw_words))

        if should_ban and message.guild and message.guild.me and message.guild.me.guild_permissions.ban_members:
            reason = ("Auto-ban: NSFW invite" if is_nsfw_target else "Auto-ban: suspected NSFW spam")
            try:
                await message.guild.ban(message.author, reason=f"{reason} (guild: {target_name})", delete_message_days=0)
            except Exception:
                pass
            try:
                await message.delete()
            except Exception:
                pass
            try:
                await send_ban_embeds(message.guild, message.author, f"{reason} (guild: {target_name})")
            except Exception:
                pass
    except Exception as e:
        logging.warning("[InviteGuard] Error: %s", e)
