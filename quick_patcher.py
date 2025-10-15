#!/usr/bin/env python3
"""
quick_patcher.py
Menjalankan semua patch yang diperlukan.

Usage:
  python quick_patcher.py
"""
import subprocess, sys, os

def run(cmd):
    print("$ " + " ".join(cmd))
    rc = subprocess.call(cmd, shell=False)
    if rc != 0:
        sys.exit(rc)

def main():
    base = os.path.dirname(__file__) or "."
    patch = os.path.join(base, "patches", "patch_dummy_waitready.py")
    target = os.path.join("satpambot","bot","modules","discord_bot","helpers","smoke_utils.py")
    if not os.path.exists(patch):
        print("Patch script tidak ditemukan:", patch)
        sys.exit(1)
    run([sys.executable, patch, target])
    print("Semua patch selesai.")

if __name__ == "__main__":
    main()
