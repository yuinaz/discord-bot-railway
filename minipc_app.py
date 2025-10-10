#!/usr/bin/env python3
"""
minipc_app.py — Single-file local/MINIPC runner for SatpamLeina.

- Tidak mengubah main.py lama (tetap memanggil _entry.main()).
- Auto-detect SatpamBot.env dari beberapa lokasi (termasuk folder EXE saat dibundle).
- Graceful shutdown: Ctrl+C, SIGTERM, (opsional) event close Windows jika pywin32 tersedia.
- Bisa dijalankan langsung sebagai script atau dibundle jadi .exe (PyInstaller).

Usage:
  python minipc_app.py               # auto detect env
  python minipc_app.py --env path    # pakai env tertentu
  python minipc_app.py --strict      # error jika env tidak ditemukan
  python minipc_app.py --override    # timpa variabel env yang sudah ada

Saat dibundle jadi .exe:
  - Letakkan SatpamBot.env di folder yang sama dengan .exe untuk auto-detect.
"""

from __future__ import annotations

import argparse
import os
import sys
import signal
import traceback
from pathlib import Path

# ---------------------- UTIL: PRINT + ENV LOADER ----------------------------- #
def _eprint(*a, **kw):
    print(*a, **kw, file=sys.stderr)

def _read_env_file(p: str) -> dict:
    data = {}
    p = Path(p)
    if not p.exists():
        return data
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data

def _try_locations() -> Path | None:
    # urutan: arg --env, CWD/SatpamBot.env, script_dir/SatpamBot.env, exe_dir/SatpamBot.env
    # Lokasi exe_dir hanya relevan untuk PyInstaller.
    candidates = []
    cwd = Path.cwd()
    candidates.append(cwd / "SatpamBot.env")
    try:
        script_dir = Path(__file__).resolve().parent
        candidates.append(script_dir / "SatpamBot.env")
    except Exception:
        pass
    # PyInstaller support
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "SatpamBot.env")

    for c in candidates:
        if c.exists():
            return c
    return None

def load_env_file(path: str, override: bool = False) -> dict:
    data = _read_env_file(path)
    for k, v in data.items():
        if override or (k not in os.environ):
            os.environ[k] = v
    return data

# ---------------------- GRACEFUL SHUTDOWN HANDLERS ------------------------- #
_SHUTDOWN_FLAG = False

def _set_shutdown():
    global _SHUTDOWN_FLAG
    _SHUTDOWN_FLAG = True

def _install_signal_handlers():
    def _handle(sig, frame):
        # Pastikan SIGINT benar-benar memicu KeyboardInterrupt agar Ctrl+C langsung stop.
        _set_shutdown()
        if sig == signal.SIGINT:
            raise KeyboardInterrupt
        if sig == signal.SIGTERM:
            raise SystemExit(0)

    try:
        signal.signal(signal.SIGINT, _handle)   # Ctrl+C
    except Exception:
        pass
    try:
        signal.signal(signal.SIGTERM, _handle)  # kill/terminate
    except Exception:
        pass

    # Windows console close event (opsional)
    try:
        import win32api  # type: ignore
        def _on_close(ctrl_type):
            _set_shutdown()
            # return True -> event consumed; biarkan proses keluar normal
            return True
        win32api.SetConsoleCtrlHandler(_on_close, True)  # noqa
    except Exception:
        pass

# ---------------------- DELEGATE KE ENTRY ASLI ----------------------------- #
def run_main():
    # Import malas (agar error import terlihat setelah ENV terpasang)
    try:
        import _entry as _entry  # modul asli project (memunculkan log: INFO:entry.main:...)
    except Exception as e:
        _eprint(f"Gagal import _entry: {e}")
        raise
    _entry.main()

def main(argv: list[str] | None = None):
    argv = argv or sys.argv[1:]
    ap = argparse.ArgumentParser(prog="minipc_app", add_help=True)
    ap.add_argument("--env", help="path ke SatpamBot.env", default=None)
    ap.add_argument("--strict", action="store_true", help="error jika env tidak ditemukan")
    ap.add_argument("--override", action="store_true", help="timpa environment yang sudah ada dengan isi .env")
    args = ap.parse_args(argv)

    env_path = args.env or os.environ.get("SATPAM_ENV_FILE")
    if env_path and Path(env_path).exists():
        load_env_file(env_path, override=args.override)
        print(f"✅ Loaded env file: {Path(env_path).name}")
    else:
        auto = _try_locations()
        if auto and auto.exists():
            load_env_file(str(auto), override=args.override)
            print(f"✅ Loaded env file: {auto.name}")
        else:
            msg = "⚠️ SatpamBot.env tidak ditemukan (pakai --env PATH atau letakkan di folder yang sama)."
            if args.strict:
                _eprint(msg)
                sys.exit(2)
            else:
                print(msg)

    _install_signal_handlers()

    try:
        run_main()
    except KeyboardInterrupt:
        # Tangkap agar tidak ada traceback panjang
        print("\n👋 Terima kasih. Shutting down gracefully…")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        _eprint(f"\n💥 Unhandled error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
