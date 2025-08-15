
# Exclude cogs that cause duplicate commands or are intentionally disabled
COGS_EXCLUDE = {
    'modules.discord_bot.cogs.moderation_test',
    'modules.discord_bot.cogs.slash_basic',
}


from __future__ import annotations
import logging, pkgutil, os
from typing import List

logger = logging.getLogger("cogs_loader")

PRIORITY = [
    "modules.discord_bot.cogs.fast_guard",
    "modules.discord_bot.cogs.anti_image_phish_advanced",
    "modules.discord_bot.cogs.presence_fix",
    "modules.discord_bot.cogs.status_sticky_auto",
    "modules.discord_bot.cogs.slash_sync",
    "modules.discord_bot.cogs.testban_hybrid",
    "modules.discord_bot.cogs.status_sticky_manual_proxy",
]

# Skip list for production (can be overridden by ENV)
DEFAULT_SKIP = {"commands_probe"}
if os.getenv("DEBUG_PROBE", "0") == "1":
    DEFAULT_SKIP.discard("commands_probe")

def _iter_cogs_package() -> List[str]:
    import modules.discord_bot.cogs as cogs_pkg
    names = []
    for mod in pkgutil.iter_modules(cogs_pkg.__path__, cogs_pkg.__name__ + "."):
        if not mod.ispkg:
            names.append(mod.name)
    return sorted(set(names))

async def load_all(bot):
    loaded = set()
    for name in PRIORITY:
        try:
            base = name.split(".")[-1]
            if base in DEFAULT_SKIP:
                logger.info(f"[cogs_loader] skip (default): {name}")
                continue
            await bot.load_extension(name)
            logger.info(f"[cogs_loader] loaded {name}")
            loaded.add(base)
        except Exception as e:
            logger.warning(f"[cogs_loader] skip {name}: {e}")
    for name in _iter_cogs_package():
        base = name.split(".")[-1]
        if base in loaded or base in DEFAULT_SKIP:
            if base in DEFAULT_SKIP:
                logger.info(f"[cogs_loader] skip (default): {name}")
            continue
        try:
            await bot.load_extension(name)
            logger.info(f"[cogs_loader] loaded {name}")
        except Exception as e:
            logger.warning(f"[cogs_loader] skip {name}: {e}")

async def load_cogs(bot):
    return await load_all(bot)