"""
MiniPC runner (asyncio-safe + Ctrl+C friendly)

- Prevents nested asyncio.run() explosions by monkey-patching asyncio.run to be loop-smart.
- Delegates to run_local_minipc.run() if available; otherwise falls back to entry.main.run().
- Graceful Ctrl+C: tries best-effort shutdown, then exits cleanly.
"""

import os
import sys
import time
import types
import signal
import asyncio
import logging

log = logging.getLogger("minipc_app")
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)

# ---- asyncio.run monkey-patch (safe in running loop) ---------------------
def _smart_asyncio_run(coro):
    """
    If there's no running loop, behave like asyncio.run.
    If there *is* a running loop (e.g. inside an async main), schedule the coroutine as a task.
    """
    if not asyncio.iscoroutine(coro) and callable(coro):
        # tolerate accidental passing of coroutine function
        coro = coro()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # don't crash; schedule and return the task
        return loop.create_task(coro)
    else:
        return asyncio.run(coro)

# apply the patch early so downstream modules use it.
asyncio.run = _smart_asyncio_run  # type: ignore

# ---- graceful shutdown helpers ------------------------------------------
_shutdown_requested = False

def _request_shutdown():
    global _shutdown_requested
    if _shutdown_requested:
        return
    _shutdown_requested = True
    log.info("Shutdown requested — attempting graceful stop...")

    # Best-effort: try to call common shutdown hooks if they exist
    for mod_name, attr_names in [
        ("satpambot.bot.modules.discord_bot.shim_runner",
            ("request_shutdown", "request_exit", "stop", "shutdown", "graceful_stop",)),
        ("entry.main", ("request_shutdown", "request_exit", "stop", "shutdown", "graceful_stop",)),
    ]:
        try:
            mod = __import__(mod_name, fromlist=["*"])
            for a in attr_names:
                fn = getattr(mod, a, None)
                if callable(fn):
                    try:
                        fn()  # sync hint
                        log.info("Called %s.%s()", mod_name, a)
                        break
                    except TypeError:
                        # maybe async
                        try:
                            res = fn()
                            if asyncio.iscoroutine(res):
                                asyncio.run(res)  # patched run is safe
                                log.info("Awaited %s.%s()", mod_name, a)
                                break
                        except Exception as e:
                            log.warning("Error calling %s.%s(): %s", mod_name, a, e)
        except Exception:
            pass

def _signal_handler(sig, frame):
    log.info("Received %s", sig)
    _request_shutdown()
    # give a moment for pending tasks to cancel
    time.sleep(0.5)
    # hard-exit fallback
    try:
        # flush logs
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    # final exit
    os._exit(0)

def main():
    # wire signals as early as possible
    try:
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
    except Exception:
        # on some platforms (e.g., Windows threads) this can fail; ignore
        pass

    # Delegation preference:
    #   1) run_local_minipc.run()
    #   2) entry.main.run()
    #   3) entry.main.main()
    # All calls are safe even if downstream does asyncio.run internally.
    delegate = None

    try:
        import run_local_minipc as rl
        if hasattr(rl, "run") and callable(rl.run):
            log.info("Delegating run to run_local_minipc.run()")
            delegate = rl.run
    except Exception as e:
        log.info("run_local_minipc not available or failed to import: %s", e)

    if delegate is None:
        try:
            import entry.main as entry_main
            if hasattr(entry_main, "run") and callable(entry_main.run):
                log.info("Delegating run to entry.main.run()")
                delegate = entry_main.run
            elif hasattr(entry_main, "main") and callable(entry_main.main):
                log.info("Delegating run to entry.main.main()")
                delegate = entry_main.main
        except Exception as e:
            log.error("entry.main not available: %s", e)

    if delegate is None:
        log.error("No runnable entry found. Expected run_local_minipc.run() or entry.main.run()/main().")
        sys.exit(2)

    try:
        res = delegate()
        # If delegate returns a coroutine, schedule safely (patched asyncio.run)
        if asyncio.iscoroutine(res):
            asyncio.run(res)
    except KeyboardInterrupt:
        _request_shutdown()
        log.info("KeyboardInterrupt — exiting.")
    except Exception as e:
        log.error("💥 Unhandled error bubbled up from main(): %s", e, exc_info=True)
        _request_shutdown()
        sys.exit(1)

if __name__ == "__main__":
    main()