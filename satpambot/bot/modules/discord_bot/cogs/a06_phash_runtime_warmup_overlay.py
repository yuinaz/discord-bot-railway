# a06_phash_runtime_warmup_overlay.py
import logging, asyncio, inspect
from discord.ext import commands

log = logging.getLogger(__name__)

def _maybe_len(x):
    try:
        return len(x)
    except Exception:
        return None

class PhashRuntimeWarmupOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _collect_entries_from_indexers(self):
        entries = []
        mods = []
        candidates = [
            "satpambot.bot.modules.discord_bot.cogs.imagephish_ref_indexer_v2",
            "satpambot.bot.modules.discord_bot.cogs.imagephish_ref_indexer",
            "modules.discord_bot.cogs.imagephish_ref_indexer_v2",
            "modules.discord_bot.cogs.imagephish_ref_indexer",
        ]
        for name in candidates:
            try:
                mod = __import__(name, fromlist=["*"])
                mods.append(mod)
            except Exception:
                continue
        for mod in mods:
            for attr in ("get_cache", "get_entries", "cache", "CACHE", "PHASH_CACHE", "ENTRIES", "INDEX", "DB"):
                try:
                    obj = getattr(mod, attr, None)
                    if obj is None: continue
                    val = obj() if callable(obj) else obj
                    if isinstance(val, dict):
                        entries.extend(val.items())
                    elif isinstance(val, (list, tuple, set)):
                        entries.extend(list(val))
                except Exception:
                    continue
        seen, uniq = set(), []
        for it in entries:
            key = it[0] if isinstance(it, (list, tuple)) and it else it
            if key in seen: continue
            seen.add(key); uniq.append(it)
        return uniq

    async def _get_runtime_db(self):
        candidates = [
            "satpambot.bot.modules.discord_bot.cogs.anti_image_phash_runtime",
            "satpambot.bot.modules.discord_bot.cogs.anti_image_phash_runtime_strict",
            "modules.discord_bot.cogs.anti_image_phash_runtime",
            "modules.discord_bot.cogs.anti_image_phash_runtime_strict",
        ]
        for name in candidates:
            try:
                mod = __import__(name, fromlist=["*"])
            except Exception:
                continue
            for attr in ("RUNTIME_DB", "runtime_db", "DB", "db"):
                db = getattr(mod, attr, None)
                if db is not None:
                    return (mod, db)
            for fn in ("reload_from_sources", "reload_runtime_db", "warm_from_cache", "reseed_from_indexers"):
                if hasattr(mod, fn) and callable(getattr(mod, fn)):
                    return (mod, fn)
        return (None, None)

    async def _try_warmup(self):
        mod, obj = await self._get_runtime_db()
        if not mod or not obj:
            log.info("[phash_warmup] runtime DB module not found; skip")
            return
        if isinstance(obj, str) and hasattr(mod, obj) and callable(getattr(mod, obj)):
            try:
                await asyncio.sleep(0)
                fn = getattr(mod, obj)
                return await fn() if inspect.iscoroutinefunction(fn) else fn()
            except Exception as e:
                log.info("[phash_warmup] %s() failed: %r", obj, e)
                return
        db = obj
        entries = await self._collect_entries_from_indexers()
        if not entries:
            log.info("[phash_warmup] no entries; skip")
            return
        for method in ("update", "load", "extend", "add_many", "add"):
            f = getattr(db, method, None)
            if callable(f):
                try:
                    if method == "update":
                        d = {}
                        for it in entries:
                            if isinstance(it, (list, tuple)) and len(it) >= 2:
                                d[it[0]] = it[1]
                        if d: f(d); break
                    else:
                        f(entries); break
                except Exception:
                    continue

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(6.0)
        try:
            await self._try_warmup()
        except Exception as e:
            log.info("[phash_warmup] warmup skipped: %r", e)

async def setup(bot):
    await bot.add_cog(PhashRuntimeWarmupOverlay(bot))
