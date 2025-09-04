from __future__ import annotations
# Legacy re-exports for compatibility with old imports
import re as re
import json as json
try:
    from . import threadlog, static_cfg, modlog, img_hashing, lists_loader, github_sync, log_utils  # noqa: F401
except Exception:
    # keep init lightweight; ignore failures
    pass
