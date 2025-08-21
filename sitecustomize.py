import importlib, sys
def _patch(mod):
    try:
        fn=getattr(mod,'create_app',None)
        if fn and not getattr(fn,'_sb_wrapped',False):
            def _wrap(*a,**k):
                app=fn(*a,**k)
                try:
                    from satpambot.dashboard.webui import register_webui_builtin as _reg
                    _reg(app)
                except Exception:
                    pass
                return app
            _wrap._sb_wrapped=True
            mod.create_app=_wrap
    except Exception:
        pass
if 'app' in sys.modules: _patch(sys.modules['app'])
_real=importlib.import_module
def import_module(name, package=None):
    m=_real(name, package)
    if name=='app': _patch(m)
    return m
importlib.import_module = import_module
