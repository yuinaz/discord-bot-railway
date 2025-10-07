#!/usr/bin/env python
import sys, platform, importlib, importlib.metadata as md

PKGS = [
    ("discord.py", "discord"),
    ("flask", "flask"),
    ("aiohttp", "aiohttp"),
    ("httpx", "httpx"),
    ("openai", "openai"),
    ("numpy", "numpy"),
    ("psutil", "psutil"),
    ("Pillow", "PIL"),
]

def get_ver(display, pkg):
    try:
        return md.version(display)
    except md.PackageNotFoundError:
        try:
            m = importlib.import_module(pkg)
            v = getattr(m, "__version__", None)
            return str(v) if v else "unknown"
        except Exception:
            return "missing"

def header():
    print("=== ENV CHECK ===")
    print(f"Python: {platform.python_version()} ({platform.python_build()[0]}) [{platform.platform()}]")
    for disp, imp in PKGS:
        print(f"{disp:<14}: {get_ver(disp, imp)}")

def _v(s):
    try:
        from packaging import version as _ver
        return _ver.parse(s)
    except Exception:
        return None

def compat():
    problems = []

    # OpenCV vs NumPy
    try:
        cv = md.version("opencv-python-headless")
    except md.PackageNotFoundError:
        cv = None
    try:
        np = md.version("numpy")
    except md.PackageNotFoundError:
        np = None
    if cv and np:
        if cv.startswith("4.12") and _v(np) and _v(np) >= _v("2.3.0"):
            problems.append(f"OpenCV {cv} tidak kompatibel dengan NumPy {np} (butuh NumPy < 2.3).")

    # httpx vs googletrans
    gt_ver = None
    for name in ("googletrans", "googletrans-py"):
        try:
            gt_ver = md.version(name)
            if gt_ver: break
        except md.PackageNotFoundError:
            pass
    try:
        hx = md.version("httpx")
    except md.PackageNotFoundError:
        hx = None
    if gt_ver and hx and _v(hx) and _v(hx) >= _v("0.28.0"):
        print(f"[warn] googletrans terdeteksi (v{gt_ver}) + httpx {hx}. Pastikan fork kompatibel (disarankan googletrans-py).")

    # tzdata for Asia/Jakarta
    try:
        from zoneinfo import ZoneInfo
        _ = ZoneInfo("Asia/Jakarta")
    except Exception:
        problems.append("tzdata tidak ditemukan untuk Asia/Jakarta. Install: pip install -U tzdata")

    if problems:
        print("== COMPAT CHECK: FAIL ==")
        for p in problems:
            print(" -", p)
        sys.exit(2)
    else:
        print("== COMPAT CHECK: OK ==")

def main():
    header()
    compat()

if __name__ == "__main__":
    main()
