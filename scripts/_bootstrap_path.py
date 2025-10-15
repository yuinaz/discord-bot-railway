# scripts/_bootstrap_path.py
# Ensure repo-root on sys.path and make printing Windows-safe.
import os, sys, pathlib

# Add repo root (parent of /scripts) to sys.path
try:
    here = pathlib.Path(__file__).resolve()
    repo_root = here.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
except Exception:
    pass

# Force UTF-8 stdout/stderr if supported
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Helper to sanitize strings for legacy code pages (e.g., cp932)
_TRANS = str.maketrans({
    "\u2014": "-",  # em dash
    "\u2013": "-",  # en dash
    "\u2019": "'",  # right single quote
    "\u2018": "'",  # left single quote
    "\u201c": '"',  # left double quote
    "\u201d": '"',  # right double quote
    "\u2026": "...",# ellipsis
    "\u00a0": " ",  # nbsp
})
def safe_print(*args, **kwargs):
    def _coerce(x):
        try:
            s = str(x)
        except Exception:
            s = repr(x)
        return s.translate(_TRANS)
    print(*map(_coerce, args), **kwargs)