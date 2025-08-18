from __future__ import annotations
import logging, pkgutil, importlib, os
logger = logging.getLogger(__name__)

DEFAULT_SKIP = {'commands_probe'}
# allow disabling via env, but don't force-disable critical cogs
DISABLED_COGS = set(x.strip() for x in (os.getenv('DISABLED_COGS') or '').split(',') if x.strip())

CANDIDATE_PACKAGES = [
    'satpambot.bot.modules.discord_bot.cogs',
    'bot.modules.discord_bot.cogs',
    'modules.discord_bot.cogs',
    'discord_bot.cogs',
]

def _iter_pkg(pkgname: str):
    try:
        pkg = importlib.import_module(pkgname)
    except Exception:
        return []
    try:
        for m in pkgutil.iter_modules(pkg.__path__, pkgname + '.'):
            yield m.name
    except Exception:
        return []

def _iter_all():
    seen=set()
    for base in CANDIDATE_PACKAGES:
        for name in _iter_pkg(base):
            leaf = name.rsplit('.',1)[-1]
            if leaf.startswith('_'): 
                continue
            if name not in seen:
                seen.add(name)
                yield name

async def load_all(bot):
    loaded=set()
    for name in _iter_all():
        leaf = name.rsplit('.',1)[-1]
        if leaf in loaded or leaf in DEFAULT_SKIP or leaf in DISABLED_COGS:
            continue
        try:
            await bot.load_extension(name)
            loaded.add(leaf)
            logger.info("[cogs_loader] loaded %s", name)
        except Exception:
            logger.debug("[cogs_loader] skip %s", name, exc_info=True)

async def load_cogs(bot):
    return await load_all(bot)
