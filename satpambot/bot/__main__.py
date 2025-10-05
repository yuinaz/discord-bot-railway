#!/usr/bin/env python3
"""Executable entrypoint for `python -m satpambot.bot`.

Robustly calls the bot runner in `satpambot.bot.modules.discord_bot.shim_runner`,
supporting both sync and async entrypoints. Imports are local to functions to
avoid lint (ruff I001) without changing project config.
"""

def _run_coro(coro) -> None:
    # Local import to avoid global import block
    import asyncio

    try:
        asyncio.run(coro)
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(coro)
        else:
            raise

def _run() -> None:
    # Late imports keep module tiny and lint-friendly
    import inspect
    try:
        from satpambot.bot.modules.discord_bot import shim_runner as _shim
    except Exception as e:  # pragma: no cover
        raise SystemExit(f"[satpambot.bot.__main__] failed to import shim_runner: {e}")

    candidates = ("main", "run", "run_bot", "start", "start_bot")
    for name in candidates:
        fn = getattr(_shim, name, None)
        if not callable(fn):
            continue

        if inspect.iscoroutinefunction(fn):
            _run_coro(fn())
            return

        result = fn()
        if inspect.iscoroutine(result):
            _run_coro(result)
        return

    raise SystemExit(
        "[satpambot.bot.__main__] No suitable entry function found in shim_runner "
        f"(tried: {', '.join(candidates)})."
    )

if __name__ == "__main__":
    _run()
