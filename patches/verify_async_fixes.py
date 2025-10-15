#!/usr/bin/env python3
import os, pathlib

TARGETS = [
    "a06_status_coalescer_wildcard_overlay.py",
    "learning_passive_observer.py",
    "learning_passive_observer_persist.py",
    "phish_log_sticky_example.py",
    "phish_log_sticky_guard.py",
    "qna_dual_provider.py",
]

def main():
    root = pathlib.Path.cwd()
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "venv", ".venv", "__pycache__")]
        for fn in filenames:
            if fn in TARGETS:
                found.append(os.path.join(dirpath, fn))
    if not found:
        print("[warn] No target files found.")
        return
    for p in found:
        t = open(p, "r", encoding="utf-8").read()
        ok1 = "async def setup(bot):" in t
        ok2 = "_satpam_safe_add_cog" in t and "await _satpam_safe_add_cog(" in t
        print(f"[{'OK' if ok1 and ok2 else 'BAD'}] {p}")
if __name__ == "__main__":
    main()
