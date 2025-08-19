import importlib, logging, pkgutil
from typing import Iterable, List

log = logging.getLogger("cogs_loader")

COG_ROOTS = [
    "satpambot.bot.modules.discord_bot.cogs",
    "modules.discord_bot.cogs",
    "discord_bot.cogs",
]

PRESENCE_DUPES = {"presence_sticky", "presence_clock_sticky", "status_sticky_auto"}
PREFER_KEEP = {"sticky_guard"}

def _iter_modules(pkg_name: str) -> Iterable[str]:
    try:
        pkg = importlib.import_module(pkg_name)
        if not hasattr(pkg, "__path__"):
            return []
        for m in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
            name = m.name.rsplit(".", 1)[-1]
            if name.startswith("_") or name == "__pycache__":
                continue
            yield m.name
    except Exception as e:
        log.debug("skip pkg %s: %s", pkg_name, e)
        return []

def _dedupe_presence(mod_names: List[str]) -> List[str]:
    keep = []
    seen_presence = False
    has_sticky_guard = any(n.endswith(".sticky_guard") for n in mod_names)
    for full in mod_names:
        short = full.rsplit(".",1)[-1]
        if short in PREFER_KEEP and has_sticky_guard:
            keep.append(full); continue
        if short in PRESENCE_DUPES:
            if has_sticky_guard:
                log.info("[cogs_loader] skip presence dup: %s (sticky_guard preferred)", full); continue
            if seen_presence:
                log.info("[cogs_loader] skip presence dup: %s", full); continue
            seen_presence = True; keep.append(full)
        else:
            keep.append(full)
    return keep

async def load_all(bot):
    loaded = 0
    for root in COG_ROOTS:
        mods = list(_iter_modules(root))
        if not mods: continue
        mods.sort()
        mods = _dedupe_presence(mods)
        for mpath in mods:
            try:
                await bot.load_extension(mpath)
                log.info("[cogs_loader] loaded %s", mpath); loaded += 1
            except Exception as e:
                log.exception("[cogs_loader] failed %s: %s", mpath, e)
    if loaded == 0:
        log.warning("[cogs_loader] no cogs loaded from roots=%s", COG_ROOTS)
