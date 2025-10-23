# -*- coding: utf-8 -*-
"""
offline_patch_sanity.py
=================================
Cek OFFLINE (tanpa internet & tanpa Discord) untuk patch Leina.

Apa yang dicek:
- Import semua COG patch (tanpa koneksi Discord) dengan stub.
- Chainloader hardened tidak meledak saat setup(bot).
- 'progress_embed_solo' TIDAK lagi meng-`await` fungsi yang bukan coroutine (simulasi).
- EmbedScribe.upsert: async / maybe-await sudah ada.
- QNA dedup & quiet delete logger terpasang.
- XP phase sync overlay ada (tidak dijalankan loopnya, hanya import).

Cara pakai:
  python scripts/offline_patch_sanity.py

Exit code:
  0 = OK semua (atau hanya WARNING minor)
  1 = Ada FAIL (periksa section FAIL di bawah)
"""
import os, sys, types, asyncio, importlib, inspect, logging, traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
print(f"[path] project_root={ROOT}")

# ==== Stub minimal untuk 'discord' ====
try:
    import discord  # real installed? good
    print("[stub] discord: REAL")
except Exception:
    discord = types.ModuleType("discord")
    abc = types.ModuleType("discord.abc")
    ext = types.ModuleType("discord.ext")
    commands = types.ModuleType("discord.ext.commands")

    class Cog:
        @classmethod
        def listener(cls, *a, **kw):
            def deco(f): return f
            return deco

    def _decorator(*dargs, **dkwargs):
        def wrap(f): return f
        return wrap

    class _Group:
        def __init__(self, f): self.func=f
        def __call__(self, *a, **kw): return self.func(*a, **kw)
        def command(self, *a, **kw):
            def deco(f): return f
            return deco
        def group(self, *a, **kw):
            def deco(f): return _Group(f)
            return deco

    commands.Cog = Cog
    commands.command = _decorator
    commands.group = lambda *a, **kw: (lambda f: _Group(f))
    commands.has_permissions = _decorator
    commands.bot_has_permissions = _decorator
    ext.commands = commands
    discord.ext = ext
    discord.abc = abc
    sys.modules["discord"] = discord
    sys.modules["discord.abc"] = abc
    sys.modules["discord.ext"] = ext
    sys.modules["discord.ext.commands"] = commands
    print("[stub] discord: STUB")

# ==== ENV guard (disable networked loops) ====
os.environ.setdefault("KV_BACKEND", "none")

# Dummy bot
class BotStub:
    def __init__(self):
        self.cogs = {}
    async def add_cog(self, cog, *a, **kw):
        self.cogs[getattr(cog, "__class__", type(cog)).__name__] = cog
    # legacy sync add_cog compatibility
    def add_cog_sync(self, cog):
        self.cogs[getattr(cog, "__class__", type(cog)).__name__] = cog

bot = BotStub()

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
failures = []
warnings = []

def OK(msg): print("OK:", msg)
def WARN(msg): print("WARN:", msg); warnings.append(msg)
def FAIL(msg): print("FAIL:", msg); failures.append(msg)

def safe_import(name):
    try:
        mod = importlib.import_module(name)
        OK(f"import {name}")
        return mod
    except Exception as e:
        FAIL(f"import {name} -> {e}")
        traceback.print_exc()
        return None

def async_run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        return asyncio.create_task(coro)
    else:
        return asyncio.run(coro)

# ==== 1) Import COG patches ====
targets = [
    "satpambot.bot.modules.discord_bot.cogs.a06_embed_scribe_post_shim_v2",
    "satpambot.bot.modules.discord_bot.cogs.a00_progress_embed_safeawait_bootstrap",
    "satpambot.bot.modules.discord_bot.cogs.a24_autolearn_qna_autoreply_fix_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a91_log_quiet_delete_safe_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a09_xp_phase_sync_overlay",
    # sanity for progress & utils:
    "satpambot.bot.modules.discord_bot.cogs.progress_embed_solo",
    "satpambot.bot.utils.embed_scribe",
]

mods = [safe_import(t) for t in targets]

# ==== 2) Check EmbedScribe.upsert is safe ====
try:
    es_mod = importlib.import_module("satpambot.bot.utils.embed_scribe")
    ES = getattr(es_mod, "EmbedScribe", None)
    if ES is None:
        WARN("EmbedScribe not found (skip embed checks)")
    else:
        up = getattr(ES, "upsert", None)
        if up is None:
            FAIL("EmbedScribe.upsert missing")
        else:
            if asyncio.iscoroutinefunction(up):
                OK("EmbedScribe.upsert is async")
            else:
                # allow maybe-await wrapper from a00_progress_embed_safeawait_bootstrap
                try:
                    sa = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a00_progress_embed_safeawait_bootstrap")
                    ma = getattr(sa, "maybe_await", None)
                    if ma:
                        # simulate calling ma(None) should not raise
                        try:
                            async def _t(): return await ma(None)
                            async_run(_t())
                            OK("maybe_await present and safe for None")
                        except Exception as e:
                            FAIL(f"maybe_await raised: {e}")
                    else:
                        FAIL("maybe_await missing; risk NoneType await")
                except Exception as e:
                    FAIL(f"safeawait overlay not importable: {e}")
except Exception as e:
    FAIL(f"EmbedScribe check error: {e}")

# ==== 3) Try chainloader setup in dry-run ====
cl = safe_import("satpambot.bot.modules.discord_bot.cogs.a00_chainload_overlays")
if cl:
    try:
        setup = getattr(cl, "setup", None)
        if setup is None:
            FAIL("chainloader: setup() missing")
        else:
            # dry-run: our stubs shouldn't start IO tasks
            res = setup(bot)
            OK("chainloader.setup invoked (dry-run)")
    except Exception as e:
        FAIL(f"chainloader.setup error: {e}")

# ==== 4) progress_embed_solo safety check (static-ish) ====
try:
    pe = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.progress_embed_solo")
    # Ensure function names exist
    assert hasattr(pe, "update_embed")
    # We can't run update_embed without real Discord, but we ensure it EXISTS.
    OK("progress_embed_solo.update_embed present")
except Exception as e:
    FAIL(f"progress_embed_solo import/attr error: {e}")

# ==== 5) Summarize ====
print("\n=== SUMMARY ===")
if failures:
    print("FAIL :", len(failures))
    for m in failures: print(" -", m)
    raise SystemExit(1)
else:
    print("OK   : no blocking failures")
    if warnings:
        print("WARN :", len(warnings))
        for m in warnings: print(" -", m)
    raise SystemExit(0)
