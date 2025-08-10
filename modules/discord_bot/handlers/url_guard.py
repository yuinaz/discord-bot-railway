# URL guard (auto)
import os, logging
from urllib.parse import urlparse
import requests
from modules.discord_bot.helpers.url_check import extract_urls, normalize_domain, check_domain_reputation, is_shortener
from modules.discord_bot.helpers.permissions import is_exempt_user, is_whitelisted_channel  # permissions import
from modules.discord_bot.helpers.db import log_action
from modules.discord_bot.helpers.log_utils import find_text_channel
from modules.discord_bot.helpers.config_manager import get_flag
from modules.discord_bot.helpers.stats import record

URL_RESOLVE_ENABLED = str(get_flag("URL_RESOLVE_ENABLED", "true")).lower()=="true"
URL_RESOLVE_TIMEOUT = float(get_flag("URL_RESOLVE_TIMEOUT","4"))
URL_AUTOBAN_CRITICAL = str(get_flag("URL_AUTOBAN_CRITICAL","true")).lower()=="true"

CRITICAL_ACTION = str(get_flag("URL_CRITICAL_ACTION","ban"))  # ban|kick|delete

def _resolve(url: str) -> str:
    if not URL_RESOLVE_ENABLED: return url
    try:
        r = requests.head(url, allow_redirects=True, timeout=URL_RESOLVE_TIMEOUT)
        if r.url: return r.url
    except Exception:
        try:
            r = requests.get(url, allow_redirects=True, timeout=URL_RESOLVE_TIMEOUT)
            if r.url: return r.url
        except Exception:
            pass
    return url

async def check_message_urls(message, bot):
    if is_whitelisted_channel(getattr(message,'channel',None)) or is_exempt_user(getattr(message,'author',None)): return
    content = message.content or ""
    urls = extract_urls(content)
    if not urls: return
    suspicious = []
    for u in urls:
        dest = u
        try:
            host = urlparse(u).netloc
            if is_shortener(host):
                dest = _resolve(u)
                host = urlparse(dest).netloc or host
            rep = check_domain_reputation(host)
            if rep in ("black","sus"):
                suspicious.append((u, dest, rep))
        except Exception as e:
            logging.debug("[URLGuard] parse error: %s", e)
            continue

    if not suspicious: return

    # Decide highest severity among URLs in message
    levels = [rep for _,_,rep in suspicious]
    level = 'black' if ('black' in levels) else 'sus'

    # Always delete the message
    try:
        await message.delete()
    except Exception:
        pass
    try:
        log_action(str(getattr(message.author,'id',0)), str(getattr(message.guild,'id',0) if message.guild else 0), 'url_scan', 'message scanned', {'suspicious': True})
    except Exception:
        pass

    # Log
    try:
        ch = find_text_channel(message.guild, "log-satpam-chat") if message.guild else None
        if ch:
            lines = []
            for src, dst, rep in suspicious:
                lines.append(f"- {src} → {dst} ({rep})")
            await ch.send("⚠️ URLGuard: dari " + message.author.mention + f" → tindakan: {{'black':'BAN','sus':'DELETE'}}[level]\n" + "\n".join(lines))
    except Exception:
        pass

    if level == 'black':
        record("url_black_actions", 1)
        if URL_AUTOBAN_CRITICAL and message.guild and CRITICAL_ACTION in ("ban","kick"):
            try:
                if CRITICAL_ACTION=="ban" and message.guild.me.guild_permissions.ban_members:
                    await message.guild.ban(message.author, reason="Auto-ban: phishing link", delete_message_days=1)
                elif CRITICAL_ACTION=="kick" and message.guild.me.guild_permissions.kick_members:
                    await message.guild.kick(message.author, reason="Auto-kick: phishing link")
            except Exception:
                pass
    else:
        record("url_sus_actions", 1)


VT_ENABLED = str(get_flag("VIRUSTOTAL_ENABLED","true")).lower()=="true"
VT_API_KEY = get_flag("VIRUSTOTAL_API_KEY", None)
VT_TIMEOUT = float(get_flag("VIRUSTOTAL_TIMEOUT","5"))
VT_CACHE_TTL = int(get_flag("VIRUSTOTAL_CACHE_TTL","3600"))  # seconds (default 1h)
_vt_cache = {}
_vt_cache_path = "data/vt_cache.json"
_vt_cache = {}

def _vt_load():
    global _vt_cache
    try:
        import json as _json, os as _os
        if _os.path.exists(_vt_cache_path):
            _vt_cache = _json.load(open(_vt_cache_path,'r',encoding='utf-8'))
    except Exception:
        _vt_cache = {}

def _vt_save():
    try:
        import json as _json, os as _os
        _os.makedirs('data', exist_ok=True)
        # prune expired
        now=int(__import__('time').time())
        for k,v in list(_vt_cache.items()):
            if isinstance(v, dict) and now - int(v.get('ts',0)) > VT_CACHE_TTL:
                _vt_cache.pop(k, None)
        _json.dump(_vt_cache, open(_vt_cache_path,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    except Exception:
        pass

def vt_check(domain_or_url: str):
    if not (VT_ENABLED and VT_API_KEY):
        return None
    import requests, json as _json
    # Use domains endpoint for simplicity
    try:
        from urllib.parse import urlparse
        host = urlparse(domain_or_url).netloc or domain_or_url
        host = host.lstrip('www.')
        _vt_load()
        host = host.lstrip("www.")
        if host in _vt_cache:
            cached = _vt_cache[host]
            now = int(__import__('time').time())
            if isinstance(cached, dict) and now - int(cached.get('ts',0)) <= VT_CACHE_TTL:
                record("vt_request_cache", 1)
                return cached.get('val')
            else:
                _vt_cache.pop(host, None)
        url = f"https://www.virustotal.com/api/v3/domains/{host}"
        r = requests.get(url, headers={"x-apikey": VT_API_KEY}, timeout=VT_TIMEOUT)
        if r.status_code != 200:
            _vt_cache[host] = {"ts": int(__import__('time').time()), "val": None}
            _vt_save()
            return None
        data = r.json()
        stats = (((data or {}).get("data") or {}).get("attributes") or {}).get("last_analysis_stats") or {}
        malicious = int(stats.get("malicious",0))
        suspicious = int(stats.get("suspicious",0))
        res = {"malicious": malicious, "suspicious": suspicious}
        _vt_cache[host] = {"ts": int(__import__('time').time()), "val": res}
        _vt_save()
        record("vt_request_net", 1)
        return res
    except Exception:
        return None
