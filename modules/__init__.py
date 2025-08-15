# Legacy import shim so 'import modules.*' works in monorepo
# It re-exports 'satpambot.bot.modules' under the name 'modules'.
import importlib as _importlib, sys as _sys

_pkg = _importlib.import_module('satpambot.bot.modules')
# Make this package look & behave like a real top-level package
__path__ = getattr(_pkg, '__path__', [])
__all__ = getattr(_pkg, '__all__', [])
# Rebind sys.modules entry so sub-imports resolve under this package
_sys.modules[__name__] = _pkg
