# -*- coding: utf-8 -*-
from __future__ import annotations
import importlib, sys

def _apply(app):
    try:
        from satpambot.dashboard.force_dashboard import install
        install(app)
    except Exception:
        pass

def _wrap(module):
    try:
        fn = getattr(module, "create_app", None)
        if fn and not getattr(fn, "_sb_force_wrapped", False):
            def _wrap_create_app(*a, **k):
                app = fn(*a, **k)
                _apply(app)
                return app
            _wrap_create_app._sb_force_wrapped = True
            module.create_app = _wrap_create_app
    except Exception:
        pass

if "app" in sys.modules:
    _wrap(sys.modules["app"])

_real = importlib.import_module
def import_module(name, package=None):
    m = _real(name, package)
    if name == "app":
        _wrap(m)
    return m

importlib.import_module = import_module
