# a00_chainload_overlays.py  (hotfix)
# Force-import critical overlays ASAP so early events route correctly.
import importlib, logging
log = logging.getLogger(__name__)

MODULES = [
    "modules.discord_bot.cogs.a01_interview_thread_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a01_interview_thread_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a00_governor_gate_neurosama_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a00_qna_allowlist_bridge_overlay",
    "modules.discord_bot.cogs.a00_governor_gate_neurosama_overlay",
    "modules.discord_bot.cogs.a00_qna_allowlist_bridge_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a27_thread_protect_shim",
    "satpambot.bot.modules.discord_bot.cogs.a26_memory_upsert_thread_router",
    "satpambot.bot.modules.discord_bot.cogs.a24_curriculum_auto_pin",
    "satpambot.bot.modules.discord_bot.cogs.a23_curriculum_admin_bridge",
    "modules.discord_bot.cogs.a27_thread_protect_shim",
    "modules.discord_bot.cogs.a26_memory_upsert_thread_router",
    "modules.discord_bot.cogs.a24_curriculum_auto_pin",
    "modules.discord_bot.cogs.a23_curriculum_admin_bridge",
    "satpambot.bot.modules.discord_bot.cogs._miner_tuning_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a00_miner_constants_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a02_balanced_interval_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a10_interval_overlay_import",
    "[chainload_hotfix] imported %s",
    "satpambot.bot.modules.discord_bot.cogs.a02_status_card_embed_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a03_cleanup_tools_overlay"
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
try:
    from . import a06_upstash_env_bridge_overlay  # noqa: F401
except Exception:
    try:
        from . import a00_upstash_env_bridge_overlay  # noqa: F401
    except Exception:
        pass

except Exception:
    try:
        from . import a00_upstash_env_bridge_overlay  # noqa: F401
    except Exception:
        pass


# Legacy sync setup wrapper (smoketest-friendly)
def setup(bot):
    try:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return loop.create_task(setup(bot))  # schedule async setup
        else:
            return asyncio.run(setup(bot))
    except Exception:
        return None
