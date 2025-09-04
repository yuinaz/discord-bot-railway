

# --- compat: expose stdlib re/json for legacy imports ---
try:
    import re as _compat_re, json as _compat_json  # noqa: F401
    re = _compat_re
    json = _compat_json
except Exception:
    pass
