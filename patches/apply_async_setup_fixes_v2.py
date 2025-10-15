#!/usr/bin/env python3
"""
Recursively patch problematic cogs so they use async setup() and await add_cog() safely.
- Works regardless of exact module package path.
- Adds LOCAL helper `_satpam_safe_add_cog` to avoid import path issues.
- Creates .bak timestamped backups.
"""
import os, re, time, pathlib, sys

PATCH_TARGET_FILENAMES = [
    "a06_status_coalescer_wildcard_overlay.py",
    "learning_passive_observer.py",
    "learning_passive_observer_persist.py",
    "phish_log_sticky_example.py",
    "phish_log_sticky_guard.py",
    "qna_dual_provider.py",
]

IGNORE_DIRS = {".git", "venv", ".venv", "__pycache__", "node_modules", "build", "dist"}

HELPER_BLOCK = """
# ---- satpambot local helper (do not remove) ----
import inspect as _sp_inspect
async def _satpam_safe_add_cog(bot, cog):
    ret = bot.add_cog(cog)
    if _sp_inspect.iscoroutine(ret):
        return await ret
    return ret
# ---- end satpambot helper ----
"""

def should_skip_dir(d: str) -> bool:
    base = os.path.basename(d.rstrip(os.sep))
    return base in IGNORE_DIRS

def find_targets(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            if fn in PATCH_TARGET_FILENAMES:
                yield os.path.join(dirpath, fn)

def inject_helper(src: str) -> str:
    if "_satpam_safe_add_cog" in src:
        return src
    return HELPER_BLOCK + "\n" + src

def ensure_async_setup(src: str) -> str:
    return re.sub(r"\bdef\s+setup\s*\(\s*bot\s*\):", "async def setup(bot):", src)

def rewrite_add_cog(src: str) -> str:
    return re.sub(r"(?<!await\s)bot\.add_cog\s*\(", "await _satpam_safe_add_cog(", src)

def patch_file(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    except Exception as e:
        print(f"[skip] read failed: {path}: {e}")
        return False
    orig = src
    src = inject_helper(src)
    src = ensure_async_setup(src)
    src = rewrite_add_cog(src)
    if src != orig:
        bak = f"{path}.bak-{int(time.time())}"
        with open(bak, "w", encoding="utf-8") as f:
            f.write(orig)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"[ok ] patched: {path}")
        return True
    else:
        print(f"[skip] already good: {path}")
        return False

def main():
    root = pathlib.Path.cwd()
    any_patched = False
    for p in find_targets(str(root)):
        any_patched |= patch_file(p)
    print("[done] Patched something." if any_patched else "[done] Nothing to patch.")
    sys.exit(0)

if __name__ == "__main__":
    main()
