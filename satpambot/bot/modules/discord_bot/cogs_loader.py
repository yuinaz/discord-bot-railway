from __future__ import annotations
import logging, pkgutil, importlib, os
logger = logging.getLogger(__name__)

DEFAULT_SKIP = {'commands_probe'}
DISABLED_COGS = set((os.getenv('DISABLED_COGS') or 'image_poster,ban_commands,ban_overrides,testban_hybrid').split(','))

def _iter_cogs_package(package_name: str):
    try:
        pkg = importlib.import_module(package_name)
    except Exception:
        return []
    try:
        for m in pkgutil.iter_modules(pkg.__path__, package_name + "."):
            yield m.name
    except Exception:
        return []

def _iter_all_candidates():
    # Try multiple layouts
    packages = [
        'satpambot.bot.modules.discord_bot.cogs',
        'modules.discord_bot.cogs',
        'discord_bot.cogs',
    ]
    seen = set()
    for pkg in packages:
        for name in _iter_cogs_package(pkg):
            if name not in seen:
                seen.add(name)
                yield name

async def load_all(bot):
    loaded = set()
    for name in _iter_all_candidates():
        base = name.split('.')[-1]
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
# ensure anti_image_phish_guard is loadable (unless disabled)
try:
    from satpambot.bot.modules.discord_bot.cogs import anti_image_phish_guard  # noqa: F401
except Exception:
    pass
