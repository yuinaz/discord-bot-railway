import asyncio, json, contextlib
from pathlib import Path
import discord

KEEPER_PATH = Path("data/keepers/keepers.json")
KEEPER_PATH.parent.mkdir(parents=True, exist_ok=True)

def _conf():
    try:
        from satpambot.config.compat_conf import get_conf as _g
    except Exception:
        try:
            from satpambot.config.runtime_memory import get_conf as _g
        except Exception:
            _g = lambda: {}
    return _g()

def _load_map():
    if not KEEPER_PATH.exists():
        return {}
    try:
        return json.loads(KEEPER_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_map(d):
    tmp = KEEPER_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(KEEPER_PATH)

async def _get_or_create_thread(ch: discord.TextChannel, name: str | None, create_ok: bool):
    if not name:
        return ch
    low = name.strip().lower()
    try:
        for th in ch.threads:
            if str(th.name).strip().lower() == low:
                return th
        async for th in ch.archived_threads(limit=50):
            if str(th.name).strip().lower() == low:
                return th
    except Exception:
        pass
    if create_ok and hasattr(ch, "create_thread"):
        try:
            th = await ch.create_thread(name=name, auto_archive_duration=1440)
            return th
        except Exception:
            pass
    return ch

async def _resolve_channel(bot, prefer_channel=None):
    cfg = _conf()
    log_id = int(str(cfg.get("LOG_CHANNEL_ID", "0")) or 0)
    thread_name = str(cfg.get("ROUTE_DEFAULT_TARGET_THREAD_NAME","neuro-lite progress")).strip()
    create_ok = str(cfg.get("ROUTE_DEFAULT_TARGET_CREATE","1")) == "1"
    force_all = str(cfg.get("ROUTE_FORCE_ALL","1")) == "1"

    ch = None
    if isinstance(prefer_channel, (discord.TextChannel, discord.Thread)) and not force_all:
        ch = prefer_channel
    elif log_id:
        ch = bot.get_channel(log_id)
    if ch is None and isinstance(prefer_channel, (discord.TextChannel, discord.Thread)):
        ch = prefer_channel

    if isinstance(ch, discord.TextChannel):
        ch = await _get_or_create_thread(ch, thread_name, create_ok)
    return ch

async def _fetch_message(ch, mid: int):
    with contextlib.suppress(Exception):
        return await ch.fetch_message(mid)
    return None

async def upsert(channel, key: str, embed: discord.Embed, *, pin=True, bot=None, route=True):
    if not embed.footer or getattr(embed.footer, "text", None) != key:
        embed.set_footer(text=key)

    ch = channel
    if route and bot is not None:
        ch = await _resolve_channel(bot, prefer_channel=channel)

    mp = _load_map()
    ch_id = str(getattr(ch, "id", 0))
    ch_map = mp.setdefault(ch_id, {})
    mid = int(ch_map.get(key, 0) or 0)

    keeper = None
    if mid:
        keeper = await _fetch_message(ch, mid)

    if keeper is None:
        with contextlib.suppress(Exception):
            async for m in ch.history(limit=100, oldest_first=False):
                for e in m.embeds:
                    if getattr(e.footer, "text", "") == key:
                        keeper = m
                        break
                if keeper: break

    if keeper is None:
        keeper = await ch.send(embed=embed, content=f"<!-- keeper:{key} -->")
        if pin:
            with contextlib.suppress(Exception): await keeper.pin()
    else:
        with contextlib.suppress(Exception): await keeper.edit(embed=embed)
        if pin:
            with contextlib.suppress(Exception):
                pins = await ch.pins()
                if keeper not in pins:
                    await keeper.pin()

    ch_map[key] = int(keeper.id)
    _save_map(mp)

    removed = 0
    with contextlib.suppress(Exception):
        async for m in ch.history(limit=150, oldest_first=False):
            if m.id == keeper.id: continue
            same = False
            for e in m.embeds:
                if getattr(e.footer, "text", "") == key:
                    same = True; break
            if same:
                with contextlib.suppress(Exception):
                    if pin:
                        pins = await ch.pins()
                        if m in pins:
                            await m.unpin()
                    await m.delete()
                    removed += 1
    if removed:
        with contextlib.suppress(Exception):
            await ch.send(content=f"<!-- janitor:{key} removed={removed} -->")
    return keeper


# ---- BACK-COMPAT SHIM (auto-appended) ----
try:
    _ES_SENTINEL  # type: ignore[name-defined]
except NameError:
    _ES_SENTINEL = True
    class EmbedScribe:
        @staticmethod
        async def upsert(bot, channel, embed, key=None, pin=True, thread_name=None, **kwargs):
            # Delegate to new function-style API if present
            try:
                up = globals().get("upsert")
                if up:
                    return await up(bot, channel, embed, key=key, pin=pin, thread_name=thread_name, **kwargs)
            except Exception:
                pass
            # Fallback to older API name if available
            we = globals().get("write_embed")
            if we:
                return await we(bot, channel, embed, key=key, pin=pin, thread_name=thread_name, **kwargs)
            raise RuntimeError("EmbedScribe shim: no upsert()/write_embed() in embed_scribe module")

        @staticmethod
        async def janitor(channel, key=None, **kwargs):
            j = globals().get("janitor")
            if j:
                return await j(channel, key=key, **kwargs)
            return False
# ---- END BACK-COMPAT SHIM ----


# ==== COMPAT PATCH (v3) — DO NOT EDIT ====
try:
    _ES_COMPAT_V3  # type: ignore[name-defined]
except NameError:
    _ES_COMPAT_V3 = True
    try:
        _OLD_EmbedScribe = EmbedScribe  # type: ignore[name-defined]
    except Exception:
        _OLD_EmbedScribe = None

    class _CompatEmbedScribe:
        def __init__(self, *args, **kwargs):
            # accept any init signature used by old callers
            self._init_args = args
            self._init_kwargs = kwargs

        async def upsert(self, *args, **kwargs):
            # Prefer new function-style API
            up = globals().get("upsert")
            if callable(up):
                return await up(*args, **kwargs)
            # Fallback to old class API if present
            if _OLD_EmbedScribe is not None:
                old_up = getattr(_OLD_EmbedScribe, "upsert", None)
                if callable(old_up):
                    try:
                        return await old_up(*args, **kwargs)
                    except TypeError:
                        # some old versions expect self; create a temp instance
                        tmp = _OLD_EmbedScribe()
                        return await old_up(tmp, *args, **kwargs)
            # Fallback to write_embed if available
            we = globals().get("write_embed")
            if callable(we):
                return await we(*args, **kwargs)
            raise RuntimeError("EmbedScribe compat v3: no upsert()/write_embed() found")

        async def janitor(self, *args, **kwargs):
            j = globals().get("janitor")
            if callable(j):
                return await j(*args, **kwargs)
            if _OLD_EmbedScribe is not None:
                old_j = getattr(_OLD_EmbedScribe, "janitor", None)
                if callable(old_j):
                    try:
                        return await old_j(*args, **kwargs)
                    except TypeError:
                        tmp = _OLD_EmbedScribe()
                        return await old_j(tmp, *args, **kwargs)
            return False

    # override any legacy class to guarantee flexible init
    EmbedScribe = _CompatEmbedScribe
# ==== END COMPAT PATCH (v3) ====

