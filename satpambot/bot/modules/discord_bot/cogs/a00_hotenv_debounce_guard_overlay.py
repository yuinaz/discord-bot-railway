
# a00_hotenv_debounce_guard_overlay.py
# Debounce repeated 'hotenv_reload' events so they broadcast once.
# FIX: Use global counters inside the inner coroutine to avoid UnboundLocalError.

import os
import asyncio
import logging
from discord.ext import commands

_PATCH_FLAG = "_patched_by_hotenv_debounce_guard"

_WINDOW_MS = int(os.getenv("HOTENV_DEBOUNCE_MS", "1200"))
_MAX_WAIT_MS = int(os.getenv("HOTENV_DEBOUNCE_MAX_MS", "3500"))

_debounce_task = None
_pending_count = 0
_last_args = ()
_last_kwargs = {}

def _patch_dispatch():
    global _debounce_task, _pending_count, _last_args, _last_kwargs

    Bot = commands.Bot
    if getattr(Bot.dispatch, _PATCH_FLAG, False):
        return

    original_dispatch = Bot.dispatch

    def patched_dispatch(self, event_name, *args, **kwargs):
        global _debounce_task, _pending_count, _last_args, _last_kwargs
        if event_name != "hotenv_reload":
            return original_dispatch(self, event_name, *args, **kwargs)

        _pending_count += 1
        _last_args = args
        _last_kwargs = kwargs

        if _debounce_task and not _debounce_task.done():
            # already scheduled; just coalesce
            return

        async def _fire_once():
            global _pending_count, _last_args, _last_kwargs
            try:
                waited = 0
                # initial window
                await asyncio.sleep(_WINDOW_MS / 1000.0)
                waited += _WINDOW_MS

                # Extend a little if more events came in, but cap.
                while _pending_count > 1 and waited < _MAX_WAIT_MS:
                    await asyncio.sleep(0.15)
                    waited += 150

                cnt = _pending_count
                _pending_count = 0
                logging.warning("[hotenv-debounce] coalesced %d hotenv_reload event(s); waited=%dms", cnt, waited)
                # forward once
                return original_dispatch(self, "hotenv_reload", *_last_args, **_last_kwargs)
            except Exception as e:
                logging.exception("[hotenv-debounce] dispatch failed: %r", e)

        _debounce_task = asyncio.create_task(_fire_once())

    patched_dispatch.__dict__[_PATCH_FLAG] = True
    Bot.dispatch = patched_dispatch
    logging.warning("[hotenv-debounce] Bot.dispatch patched (window=%dms max=%dms)", _WINDOW_MS, _MAX_WAIT_MS)

def setup_patch():
    try:
        _patch_dispatch()
    except Exception as e:
        logging.exception("[hotenv-debounce] patch failed: %r", e)

setup_patch()

async def setup(bot):
    logging.debug("[hotenv-debounce] overlay setup complete")
