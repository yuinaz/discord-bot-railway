# Legacy import shim so 'import modules.*' works in monorepo



import importlib as _importlib
import sys as _sys

_pkg = _importlib.import_module("satpambot.bot.modules")



__path__ = getattr(_pkg, "__path__", [])



__all__ = getattr(_pkg, "__all__", [])



_sys.modules[__name__] = _pkg



