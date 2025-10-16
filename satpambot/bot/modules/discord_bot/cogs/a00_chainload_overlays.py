# a00_chainload_overlays.py  (hotfix)
# Force-import critical overlays ASAP so early events route correctly.
import importlib, logging
log = logging.getLogger(__name__)

MODULES = [
    # safety first
    "satpambot.bot.modules.discord_bot.cogs.a27_thread_protect_shim",
    "satpambot.bot.modules.discord_bot.cogs.a26_memory_upsert_thread_router",
    "satpambot.bot.modules.discord_bot.cogs.a24_curriculum_auto_pin",
    "satpambot.bot.modules.discord_bot.cogs.a23_curriculum_admin_bridge",

    # compatibility for alternative namespace
    "modules.discord_bot.cogs.a27_thread_protect_shim",
    "modules.discord_bot.cogs.a26_memory_upsert_thread_router",
    "modules.discord_bot.cogs.a24_curriculum_auto_pin",
    "modules.discord_bot.cogs.a23_curriculum_admin_bridge",

    # existing overlays (keep order after our safety patches)
    "satpambot.bot.modules.discord_bot.cogs._miner_tuning_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a00_miner_constants_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a02_balanced_interval_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a10_interval_overlay_import",
]

for m in MODULES:
    try:
        importlib.import_module(m)
        log.info("[chainload_hotfix] imported %s", m)
    except Exception:
        # quiet fail, loader continues
        pass

async def setup(bot):
    # this file works via import side effects only
    return
# PATCH: ensure Upstash env bridge autoloads even on Render
from . import a06_upstash_env_bridge_overlay  # noqa: F401
