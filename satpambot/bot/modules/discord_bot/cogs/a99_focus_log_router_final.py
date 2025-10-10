# -*- coding: utf-8 -*-
# Final hard router: force all sends into LOG_CHANNEL_ID (+thread),
# never touch "rules"-like channels, deduplicate embeds, and never
# fallback to original channel on error.
import asyncio, json, logging, os, re, time
from typing import Optional, Dict, Tuple
import discord

log = logging.getLogger(__name__)

# ---------- config ----------
def _get_conf(k: str, default=None):
    v = os.getenv(k, default)
    if v is not None:
        return v
    try:
        from satpambot.config.compat_conf import get_conf as _gc  # type: ignore
        return _gc(k, default)
    except Exception:
        return default

def _log_channel_id() -> Optional[int]:
    raw = _get_conf("LOG_CHANNEL_ID", "")
    try:
        return int(str(raw).strip())
    except Exception:
        return None

# treat any variant containing "rules" as deny
def _looks_like_rules(name: str) -> bool:
    low = (name or "").lower()
    low = re.sub(r"[^\w]+", "", low)  # strip symbols/dashes/emoji borders
    return "rules" in low

_THREAD_MAP: Tuple[Tuple[re.Pattern, str], ...] = (
    (re.compile(r"NEURO[- ]?LITE GATE STATUS", re.I), "neuro-lite progress"),
    (re.compile(r"SATPAMBOT_PHASH_DB_V1", re.I), "imagephising"),
    (re.compile(r"\bML[- ]?STATE\b", re.I), "ml-state"),
    (re.compile(r"SatpamBot Status", re.I), "log restart github"),
)

_last_fp: Dict[str, Tuple[str, float, discord.Message]] = {}

def _embed_from_args(args, kwargs) -> Optional[discord.Embed]:
    e = kwargs.get("embed")
    if isinstance(e, discord.Embed):
        return e
    if args and isinstance(args[0], discord.Embed):
        return args[0]
    return None

def _guess_thread(embed: Optional[discord.Embed]) -> Optional[str]:
    if not embed:
        return None
    txt = (embed.title or "") + " " + (embed.description or "")
    for rx, name in _THREAD_MAP:
        if rx.search(txt):
            return name
    return None

async def _ensure_thread(ch: discord.TextChannel, name: str) -> discord.abc.Messageable:
    for th in ch.threads:
        if th.name == name:
            return th
    try:
        async for th in ch.archived_threads(limit=100):
            if th.name == name:
                return th
    except Exception:
        pass
    try:
        return await ch.create_thread(name=name, type=discord.ChannelType.public_thread)
    except discord.Forbidden:
        # no permission to create thread → fallback to channel
        return ch

def _fingerprint_embed(embed: discord.Embed) -> str:
    d = embed.to_dict()
    d = {k: d.get(k) for k in ("title", "description", "fields", "footer")}
    return json.dumps(d, sort_keys=True, ensure_ascii=False)

# ---------- installer ----------
_SIGNATURE = "focus_router_v7"

def _is_installed() -> bool:
    return getattr(discord.abc.Messageable, "_focus_router_signature", "") == _SIGNATURE

def _install(force: bool = False, quiet: bool = False):
    Messageable = discord.abc.Messageable
    already = _is_installed()
    if already and not force:
        return

    orig_send = getattr(Messageable, "_focus_router_orig_send", None)
    if not orig_send:
        orig_send = Messageable.send  # capture whatever is active now
    # routed send
    async def routed_send(self, *args, **kwargs):
        try:
            bot = getattr(self, "_state", None) and getattr(self._state, "client", None)
            log_id = _log_channel_id()
            if not bot or not log_id:
                # cannot resolve → just use current pipeline
                return await orig_send(self, *args, **kwargs)

            target = bot.get_channel(log_id)
            if not isinstance(target, discord.TextChannel):
                return await orig_send(self, *args, **kwargs)

            # if current channel is not the target, or it looks like "rules", route to log
            try:
                cur_id = getattr(self, "id", None)
                cur_name = (getattr(self, "name", "") or "")
            except Exception:
                cur_id, cur_name = None, ""

            must_route = (cur_id != log_id) or _looks_like_rules(cur_name)

            dest: discord.abc.Messageable = self
            if must_route:
                dest = target

            # if there is a recognized embed, move into its dedicated thread
            embed = _embed_from_args(args, kwargs)
            tname = _guess_thread(embed) if embed else None
            if tname and must_route:
                try:
                    dest = await _ensure_thread(target, tname)
                except Exception as e:
                    log.debug("[focus_final] ensure_thread fail (%s) -> fallback channel", e)
                    dest = target

            # anti-spam (only for embeds, per lane)
            if embed and isinstance(dest, (discord.Thread, discord.TextChannel)):
                lane = target.name if isinstance(dest, discord.TextChannel) else dest.name
                fp = _fingerprint_embed(embed)
                now = time.time()
                prev = _last_fp.get(lane)
                win = float(_get_conf("FOCUS_DEDUP_WINDOW_SEC", "90"))
                if prev and prev[0] == fp and (now - prev[1]) < win:
                    return prev[2]

            msg = await orig_send(dest, *args, **kwargs)

            if embed and isinstance(msg, discord.Message):
                lane = target.name if isinstance(dest, discord.TextChannel) else getattr(dest, "name", str(log_id))
                _last_fp[lane] = (_fingerprint_embed(embed), time.time(), msg)

            return msg

        except Exception as e:
            # NEVER fallback to original channel; try log channel instead
            try:
                bot = getattr(self, "_state", None) and getattr(self._state, "client", None)
                log_id = _log_channel_id()
                if bot and log_id:
                    target = bot.get_channel(log_id)
                    if isinstance(target, discord.TextChannel):
                        log.warning("[focus_final] error; rerouting to log: %s", e)
                        return await orig_send(target, *args, **kwargs)
            except Exception:
                pass
            log.exception("[focus_final] routed_send fatal; swallow to avoid spam: %s", e)
            return None  # swallow to avoid retries/spam

    # mark + install
    Messageable._focus_router_orig_send = orig_send  # type: ignore[attr-defined]
    Messageable.send = routed_send  # type: ignore[assignment]
    Messageable._focus_router_signature = _SIGNATURE  # type: ignore[attr-defined]
    if not quiet:
        log.info("[focus_log_router_final] installed")
    else:
        log.debug("[focus_log_router_final] reinstalled (quiet)")

async def _keep_installed_task():
    # assert a few times awal (senyap), lalu periodik 60s
    for _ in range(10):
        await asyncio.sleep(0.8)
        _install(force=True, quiet=True)
    while True:
        await asyncio.sleep(60.0)
        _install(force=True, quiet=True)

def setup(bot):
    _install(force=True, quiet=False)
    if hasattr(bot, "loop"):
        try:
            bot.loop.create_task(_keep_installed_task())
        except Exception:
            asyncio.create_task(_keep_installed_task())
