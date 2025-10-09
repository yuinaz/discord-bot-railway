#!/usr/bin/env python3
import argparse
import asyncio
import importlib
import inspect
import logging
import pkgutil
import sys
from types import ModuleType

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("smoke")

# ---- Dummy stubs agar banyak cog tidak error saat di-import ----
class _DummyTree:
    async def sync(self, *a, **kw):  # slash sync stub
        return []
    def add_command(self, *a, **kw):
        pass
    def remove_command(self, *a, **kw):
        pass

class _DummyBot:
    def __init__(self):
        self.cogs = {}
        self.tree = _DummyTree()
        self.guilds = []
        self.loop = asyncio.get_event_loop()
        self._is_smoke_dummy = True

    def get_cog(self, name):
        return self.cogs.get(name)

    # discord.py modern add_cog bisa sync/async (tergantung harness).
    async def add_cog(self, cog):
        name = getattr(cog, "qualified_name", cog.__class__.__name__)
        self.cogs[name] = cog
        # panggil lifecycle hook kalau ada (dan await bila coroutine)
        cl = getattr(cog, "cog_load", None)
        if cl is not None:
            res = cl()
            if inspect.isawaitable(res):
                await res

    # Banyak cogs mengharapkan ada method-method ini; kita stub.
    def add_listener(self, *a, **kw): pass
    def remove_listener(self, *a, **kw): pass
    def dispatch(self, *a, **kw): pass
    def load_extension(self, *a, **kw): pass
    def unload_extension(self, *a, **kw): pass

async def _safe_add_cog(bot: _DummyBot, cog):
    add = getattr(bot, "add_cog", None)
    if add is None:
        return
    if inspect.iscoroutinefunction(add):
        await add(cog)
    else:
        add(cog)

async def _safe_setup_module(mod: ModuleType, bot: _DummyBot):
    """
    Jalankan 'setup' dari sebuah modul cog dengan aman:
    - Jika 'setup' adalah class Cog -> instansiasi lalu add_cog
    - Jika 'setup' fungsi sync -> panggil; kalau return coroutine -> await; kalau return Cog -> add_cog
    - Jika 'setup' coroutine -> await
    - Jika tidak ada 'setup' -> dianggap idempotent
    """
    setup_attr = getattr(mod, "setup", None)
    if setup_attr is None:
        return "no-setup"

    # Case: setup adalah class yang terlihat seperti Cog
    if inspect.isclass(setup_attr):
        try:
            inst = setup_attr(bot)
            await _safe_add_cog(bot, inst)
            return "class-cog"
        except Exception:
            # tidak cocok sebagai class Cog, lanjut ke mode callable biasa
            pass

    if callable(setup_attr):
        res = setup_attr(bot)
        if inspect.isawaitable(res):
            await res
            return "awaited-func"
        # Kalau fungsi return instance Cog → add_cog
        if hasattr(res, "__class__"):
            # heuristik sederhana: ada atribut 'cog_load' atau '__cog_name__'
            if hasattr(res, "cog_load") or hasattr(res, "__cog_name__"):
                await _safe_add_cog(bot, res)
                return "returned-cog"
        return "called-sync"

    # Case: setup sudah berupa instance
    if hasattr(setup_attr, "cog_load") or hasattr(setup_attr, "__cog_name__"):
        await _safe_add_cog(bot, setup_attr)
        return "instance-cog"

    return "ignored"

def _iter_modules(pkgname: str):
    """Iter semua submodul di bawah sebuah package name."""
    pkg = importlib.import_module(pkgname)
    if hasattr(pkg, "__path__"):
        for modinfo in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
            yield modinfo.name
    else:
        yield pkgname

async def deep_check(pkgname: str, strict: bool = False):
    bot = _DummyBot()
    ok, warn, fail = [], [], []

    # Coba monkey-patch smoke_utils kalau ada, agar harness lama jadi aman
    try:
        import satpambot.bot.modules.discord_bot.helpers.smoke_utils as su  # type: ignore
        import types, inspect
        if not hasattr(su, "_smoke_patch_applied"):
            orig_add_cog = getattr(su.DummyBot, "add_cog", None)
            async def patched_add_cog(self, cog):
                # kompatibel bila orig_add_cog sync/async
                if orig_add_cog is not None:
                    res = orig_add_cog(self, cog)
                    if inspect.isawaitable(res):
                        await res
                # lalu jalankan cog_load bila perlu
                cl = getattr(cog, "cog_load", None)
                if cl is not None:
                    r = cl()
                    if inspect.isawaitable(r):
                        await r
            su.DummyBot.add_cog = patched_add_cog  # type: ignore
            su._smoke_patch_applied = True  # type: ignore
            log.info("smoke_utils.DummyBot.add_cog dipatch (maybe‑await).")
    except Exception:
        pass

    for modname in sorted(set(_iter_modules(pkgname))):
        try:
            mod = importlib.import_module(modname)
        except Exception as e:
            fail.append((modname, f"import error: {e.__class__.__name__}: {e}"))
            continue

        # Jalankan setup dengan aman bila ada
        try:
            mode = await _safe_setup_module(mod, bot)
            msg = f"{modname} — {mode}"
            ok.append(msg)
        except Exception as e:
            fail.append((modname, f"setup error: {e.__class__.__name__}: {e}"))

    # Laporan ringkas
    print("== Deep Smoke Report ==")
    for m in ok:
        print(f"OK   : {m}")
    for m, why in fail:
        print(f"FAIL : {m} :: {why}")

    return 1 if (strict and fail) else 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default="satpambot.bot.modules.discord_bot.cogs",
                    help="Root package yang akan discan (default: %(default)s)")
    ap.add_argument("--strict", action="store_true", help="Non-zero exit code bila ada FAIL")
    args = ap.parse_args()

    try:
        rc = asyncio.run(deep_check(args.package, strict=args.strict))
    except KeyboardInterrupt:
        rc = 130
    sys.exit(rc)

if __name__ == "__main__":
    main()
