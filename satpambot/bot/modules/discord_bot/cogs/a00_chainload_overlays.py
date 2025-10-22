# -*- coding: utf-8 -*-
"""
a00_chainload_overlays (hardened)
---------------------------------
Safe chainloader yang memuat daftar overlay secara berurutan.
- Tidak melempar exception jika ada modul gagal import (hanya log WARNING).
- Mendukung setup(bot) async/sync.
- Hilangkan duplikat, dukung skip via ENV CHAIN_SKIP (comma-separated).
- Tambahkan modul ekstra via ENV EXTRA_COGS (comma-separated, dotted path).

Pastikan daftar MODULES di bawah ini sesuai kebutuhanmu.
"""

import os, importlib, asyncio, logging

log = logging.getLogger(__name__)

# === DAFTAR MODUL WAJIB ===
MODULES = [
    # --- governor & qna ---
    "satpambot.bot.modules.discord_bot.cogs.a00_governor_gate_neurosama_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a00_qna_allowlist_bridge_overlay",
    # --- interview thread ---
    "satpambot.bot.modules.discord_bot.cogs.a01_interview_thread_overlay",
    # --- status card (anti-spam) & cleanup ---
    "satpambot.bot.modules.discord_bot.cogs.a02_status_card_embed_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a03_cleanup_tools_overlay",
    # --- XP autoload (agar awarder tidak warning dan store aktif) ---
    "satpambot.bot.modules.discord_bot.cogs.a00_xp_direct_autoload_overlay",
    # --- tambahkan modul lainmu di bawah ini bila perlu ---
]

def _expand_env_list(key: str):
    raw = os.getenv(key, "").strip()
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]

def _dedup_keep_order(seq):
    seen=set(); out=[]
    for x in seq:
        if x not in seen:
            out.append(x); seen.add(x)
    return out

async def _maybe_setup(mod, bot):
    """Call setup(bot) if present. Support async/sync."""
    setup = getattr(mod, "setup", None)
    if setup is None:
        # discord.py >= 2 often uses async def setup(bot)
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

    # filter prefix salah & dedup
    mods = [m for m in mods if not m.startswith("modules.discord_bot.cogs.")]
    mods = _dedup_keep_order(mods)

    for name in mods:
        try:
            mod = importlib.import_module(name)
        except Exception as e:
            log.warning("[chain] import failed %s: %r", name, e)
            continue
        await _maybe_setup(mod, bot)
        log.info("[chain] loaded %s", name)

async def setup(bot):
    await _chainload(bot)

def setup(bot):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        return loop.create_task(_chainload(bot))
    else:
        return asyncio.run(_chainload(bot))
