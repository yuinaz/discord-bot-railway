# -*- coding: utf-8 -*-
import os, importlib, asyncio, logging
log = logging.getLogger(__name__)

MODULES = [
    # base
    "satpambot.bot.modules.discord_bot.cogs.a00_governor_gate_neurosama_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a00_qna_allowlist_bridge_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a01_interview_thread_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a02_status_card_embed_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a03_cleanup_tools_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a00_xp_direct_autoload_overlay",
    # --- fixes added ---
    "satpambot.bot.modules.discord_bot.cogs.a06_embed_scribe_post_shim_v2",          # ensure EmbedScribe.post/upsert async
    "satpambot.bot.modules.discord_bot.cogs.a00_progress_embed_safeawait_bootstrap", # wrap upsert with maybe-await
    "satpambot.bot.modules.discord_bot.cogs.a24_autolearn_qna_autoreply_fix_overlay",# QNA dedup
    "satpambot.bot.modules.discord_bot.cogs.a91_log_quiet_delete_safe_overlay",      # quiet delete_safe logs
    "satpambot.bot.modules.discord_bot.cogs.a09_xp_phase_sync_overlay",              # sync phase from label
]

def _expand_env_list(key: str):
    raw = os.getenv(key, "").strip()
    if not raw: return []
    return [s.strip() for s in raw.split(",") if s.strip()]

def _dedup_keep_order(seq):
    seen=set(); out=[]
    for x in seq:
        if x not in seen:
            out.append(x); seen.add(x)
    return out

async def _maybe_setup(mod, bot):
    setup = getattr(mod, "setup", None)
    if setup:
        try:
            if asyncio.iscoroutinefunction(setup):
                await setup(bot)
            else:
                res = setup(bot)
                if asyncio.iscoroutine(res):
                    await res
        except Exception as e:
            log.warning("[chain] setup failed for %s: %r", getattr(mod, "__name__", mod), e)

async def _chainload(bot):
    skip = set(_expand_env_list("CHAIN_SKIP"))
    extra = _expand_env_list("EXTRA_COGS")
    mods = [m for m in MODULES if m not in skip] + [m for m in extra if m not in skip]
    mods = [m for m in mods if not m.startswith("modules.discord_bot.cogs.")]
    mods = _dedup_keep_order(mods)
    for name in mods:
        try:
            mod = importlib.import_module(name)
        except Exception as e:
            log.warning("[chain] import failed %s: %r", name, e); continue
        await _maybe_setup(mod, bot)
        log.info("[chain] loaded %s", name)

async def setup(bot): await _chainload(bot)

def setup(bot):
    try:
        loop = asyncio.get_event_loop()
        if loop and loop.is_running():
            return loop.create_task(_chainload(bot))
    except Exception: pass
    return asyncio.run(_chainload(bot))
