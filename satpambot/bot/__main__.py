#!/usr/bin/env python3
"""Executable entrypoint for `python -m satpambot.bot`.

Delegates to the existing shim runner without touching any config.
"""

def _run() -> None:
    # Defer import so this file stays tiny & safe
    try:
        from satpambot.bot.modules.discord_bot import shim_runner as _shim
    except Exception as e:  # pragma: no cover
        raise SystemExit(f"[satpambot.bot.__main__] failed to import shim_runner: {e}")

    # Prefer common entry names without changing user config
    for candidate in ("main", "run", "run_bot", "start", "start_bot"):
        fn = getattr(_shim, candidate, None)
        if callable(fn):
            fn()
            return

    raise SystemExit(
        "[satpambot.bot.__main__] No suitable entry function found in shim_runner "
        "(tried main/run/run_bot/start/start_bot)."
    )

if __name__ == "__main__":
    _run()
