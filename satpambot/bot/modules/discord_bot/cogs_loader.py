from __future__ import annotations
import logging, pkgutil, importlib, os

logger = logging.getLogger(__name__)
DEFAULT_SKIP = {'commands_probe'}
DISABLED_COGS = set((os.getenv('DISABLED_COGS') or 'image_poster').split(','))

def _iter_cogs_package(package_name: str):
    try:
        pkg = importlib.import_module(package_name)
    except Exception:
        return []
    for m in pkgutil.iter_modules(pkg.__path__, package_name + "."):
        yield m.name

def _iter_all_candidates():
    names = list(_iter_cogs_package("modules.discord_bot.cogs"))
    if not names:
        names = list(_iter_cogs_package("discord_bot.cogs"))
    return names

async def load_all(bot):
    loaded = set()
    for name in _iter_all_candidates():
        base = name.split(".")[-1]
        if base in loaded or base in DEFAULT_SKIP or base in DISABLED_COGS:
            continue
        try:
            await bot.load_extension(name)
            loaded.add(base)
            logger.info(f"[cogs_loader] loaded {name}")
        except Exception:
            logger.debug(f"[cogs_loader] skip {name}", exc_info=True)

async def load_cogs(bot):
    return await load_all(bot)
