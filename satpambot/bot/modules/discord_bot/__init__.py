# satpambot/bot/modules/discord_bot/__init__.py — safe re-export with bot_running shim
from __future__ import annotations
import importlib, inspect

_mod = importlib.import_module(__name__ + ".discord_bot")

# Provide a BOT_RUNNING flag and bot_running() even if discord_bot.py doesn't define it
if not hasattr(_mod, "BOT_RUNNING"):
    setattr(_mod, "BOT_RUNNING", False)

def bot_running() -> bool:
    return bool(getattr(_mod, "BOT_RUNNING", False))

# Wrap start_bot/run_bot to flip BOT_RUNNING automatically
_sb = getattr(_mod, "start_bot", None)
if _sb and inspect.iscoroutinefunction(_sb) and not getattr(_sb, "_wrapped_bot_running", False):
    async def _sb_wrap(*a, **kw):
        try:
            _mod.BOT_RUNNING = True
            return await _sb(*a, **kw)
        finally:
            _mod.BOT_RUNNING = False
    _sb_wrap._wrapped_bot_running = True  # type: ignore[attr-defined]
    setattr(_mod, "start_bot", _sb_wrap)

_rb = getattr(_mod, "run_bot", None)
if _rb and not inspect.iscoroutinefunction(_rb) and not getattr(_rb, "_wrapped_bot_running", False):
    def _rb_wrap(*a, **kw):
        try:
            _mod.BOT_RUNNING = True
            return _rb(*a, **kw)
        finally:
            _mod.BOT_RUNNING = False
    _rb_wrap._wrapped_bot_running = True  # type: ignore[attr-defined]
    setattr(_mod, "run_bot", _rb_wrap)

# Re-export
run_bot = getattr(_mod, "run_bot", None)
__all__ = ["run_bot", "bot_running"]
