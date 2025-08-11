# URL guard (auto)
async def handle_urls(message, bot):
    return await _handle_urls_impl(message, bot)

# internal below
import logging
from urllib.parse import urlparse

from modules.discord_bot.helpers.url_check import extract_urls, normalize_domain, check_domain_reputation, is_shortener
from modules.discord_bot.helpers.permissions import is_exempt_user, is_whitelisted_channel
from modules.discord_bot.helpers.log_utils import send_ban_embeds
from modules.discord_bot.helpers.db import log_action
from modules.discord_bot.helpers.config_manager import get_flag

URL_RESOLVE_ENABLED = str(get_flag("URL_RESOLVE_ENABLED", "true")).lower()=="true"
URL_AUTOBAN_CRITICAL = str(get_flag("URL_AUTOBAN_CRITICAL","true")).lower()=="true"

def _resolve(u: str, timeout: float = 4.0) -> str:
    try:
        import requests
        r = requests.get(u, timeout=timeout, allow_redirects=True)
        return r.url or u
    except Exception:
        return u

async def _handle_urls_impl(message, bot):
    try:
        if getattr(message.author, "bot", False):
            return
        if is_whitelisted_channel(getattr(message,'channel',None)) or is_exempt_user(getattr(message,'author',None)):
            return

        content = message.content or ""
        urls = extract_urls(content)
        if not urls:
            return

        suspicious = []
        for u in urls:
            dest = u
            try:
                host = urlparse(u).netloc
                if is_shortener(host) and URL_RESOLVE_ENABLED:
                    dest = _resolve(u)
                    host = urlparse(dest).netloc or host
                rep = check_domain_reputation(host)
                if rep in ('black','sus'):
                    suspicious.append((u, dest, rep))
            except Exception:
                continue

        if not suspicious:
            return

        levels = [rep for _,_,rep in suspicious]
        level = 'black' if ('black' in levels) else 'sus'

        if level == 'black' and URL_AUTOBAN_CRITICAL and message.guild and (message.guild.me and message.guild.me.guild_permissions.ban_members):
            try:
                await message.guild.ban(message.author, reason='Auto-ban: critical malicious URL', delete_message_days=0)
            except Exception:
                pass
            try:
                await message.delete()
            except Exception:
                pass
            try:
                await send_ban_embeds(message.guild, message.author, 'Auto-ban: critical malicious URL')
            except Exception:
                pass
            try:
                log_action(str(getattr(message.author,'id',0)), str(getattr(message.guild,'id',0)), 'url_black', 'auto_ban', {'urls': suspicious})
            except Exception:
                pass
        else:
            try:
                await message.delete()
            except Exception:
                pass
            try:
                log_action(str(getattr(message.author,'id',0)), str(getattr(message.guild,'id',0)), 'url_sus', 'delete', {'urls': suspicious})
            except Exception:
                pass
    except Exception:
        return
