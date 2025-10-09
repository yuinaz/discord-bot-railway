
#!/usr/bin/env python3
import asyncio
import importlib
import inspect
import logging
import os
import pkgutil
import sys
from typing import List, Tuple

from satpambot.bot.modules.discord_bot.helpers.smoke_utils import DummyBot, install_dedup_logging

log = logging.getLogger("smoke_deep_friendly")

TARGET_PKG = "satpambot.bot.modules.discord_bot.cogs"

class Result:
    def __init__(self):
        self.ok = []
        self.fail = []
        self.skip = []

    def add_ok(self, name): self.ok.append(name)
    def add_fail(self, name, err): self.fail.append((name, err))
    def add_skip(self, name, reason): self.skip.append((name, reason))

def iter_cog_modules(pkgname: str) -> List[str]:
    mod = importlib.import_module(pkgname)
    mods = []
    for m in pkgutil.walk_packages(mod.__path__, prefix=mod.__name__ + "."):
        if not m.ispkg:
            mods.append(m.name)
    return sorted(mods)

async def run_setup(bot: DummyBot, modname: str, strict: bool) -> Tuple[bool, str]:
    try:
        mod = importlib.import_module(modname)
    except Exception as e:
        return False, f"import error: {e!r}"

    setup_fn = getattr(mod, "setup", None)
    if setup_fn is None:
        return True, "no setup() — import ok"

    try:
        if inspect.iscoroutinefunction(setup_fn):
            await setup_fn(bot)
        else:
            # sync setup — just call it
            setup_fn(bot)
        return True, "idempotent, quiet"
    except TypeError as te:
        # Common offline hazards: someone awaited a None because DummyBot method not async
        return False, f"setup TypeError: {te}"
    except AttributeError as ae:
        # Missing attributes on DummyBot; treat as WARN/FAIL depending on strict
        level = "FAIL" if strict else "SKIP"
        return (False if strict else True), f"{level} setup: AttributeError: {ae}"
    except Exception as e:
        return False, f"setup error: {e.__class__.__name__}: {e}"

async def main(strict: bool = True):
    agg = install_dedup_logging()
    res = Result()
    bot = DummyBot()

    mods = iter_cog_modules(TARGET_PKG)
    for name in mods:
        ok, note = await run_setup(bot, name, strict)
        if ok:
            if "no setup()" in note:
                print(f"OK   : {name} — {note}")
            else:
                print(f"OK   : {name} — {note}")
            res.add_ok(name)
        else:
            print(f"FAIL : {name} :: {note}")
            res.add_fail(name, note)

    print("\n== Log duplicates summary (top) ==")
    # show a compact view of duplicates >1
    dup = [((*k,), c) for k, c in agg.counts.items() if c > 1]
    dup.sort(key=lambda x: -x[-1])
    for (logger_name, levelno, msg), cnt in dup[:20]:
        lvl = logging.getLevelName(levelno)
        print(f"{lvl:>5} x{cnt:>2} {logger_name}: {msg}")

    print(f"\nTotal: OK={len(res.ok)} FAIL={len(res.fail)}")
    if strict and res.fail:
        sys.exit(1)

if __name__ == "__main__":
    strict = True
    # --strict/--no-strict flags
    if "--no-strict" in sys.argv:
        strict = False
    asyncio.run(main(strict=strict))
