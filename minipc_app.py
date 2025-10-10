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
  Satukan file "SatpamBot.env" di folder yang sama dengan .exe agar auto-terbaca.
"""
from __future__ import annotations
import os, sys, argparse, signal, atexit, time

# ---------------------- ENV LOADER (tanpa dependency) ---------------------- #
ENV_CANDIDATE_NAMES = ("SatpamBot.env", "satpambot.env", ".env")

def _read_env_file(path: str) -> dict:
    data = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                # Mendukung KEY="VALUE" / KEY='VALUE' / KEY=VALUE
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                # Jangan timpa jika baris invalid
                if k:
                    data[k] = v
    except FileNotFoundError:
        pass
    return data

def _is_readable_file(p: str) -> bool:
    try:
        return os.path.isfile(p) and os.access(p, os.R_OK)
    except Exception:
        return False

def _iter_parents(start_dir: str):
    start_dir = os.path.abspath(start_dir)
    prev = None
    cur = start_dir
    while prev != cur:
        yield cur
        prev, cur = cur, os.path.dirname(cur)

def _frozen_base_dir() -> str | None:
    # Saat dibundle (PyInstaller), sys.frozen akan ada, dan sys.executable menunjuk ke file .exe
    if getattr(sys, "frozen", False):
        try:
            return os.path.dirname(sys.executable)
        except Exception:
            return None
    return None

def find_env_file(cli_env_path: str | None = None) -> str | None:
    # 1) CLI --env
    if cli_env_path and _is_readable_file(cli_env_path):
        return os.path.abspath(cli_env_path)

    # 2) Env var SATPAMBOT_ENV
    env_hint = os.environ.get("SATPAMBOT_ENV")
    if env_hint and _is_readable_file(env_hint):
        return os.path.abspath(env_hint)

    # 3) CWD dan parentnya
    for root in _iter_parents(os.getcwd()):
        for name in ENV_CANDIDATE_NAMES:
            p = os.path.join(root, name)
            if _is_readable_file(p):
                return os.path.abspath(p)

    # 4) Folder script ini & parentnya
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        for root in _iter_parents(script_dir):
            for name in ENV_CANDIDATE_NAMES:
                p = os.path.join(root, name)
                if _is_readable_file(p):
                    return os.path.abspath(p)
    except Exception:
        pass

    # 5) Jika dibundle, cek folder EXE & parentnya
    fb = _frozen_base_dir()
    if fb:
        for root in _iter_parents(fb):
            for name in ENV_CANDIDATE_NAMES:
                p = os.path.join(root, name)
                if _is_readable_file(p):
                    return os.path.abspath(p)

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
        # Biarkan KeyboardInterrupt terjadi pada loop utama (asyncio.run) agar clean
        _set_shutdown()
        # No raise; default SIGINT akan memicu KeyboardInterrupt
        # SIGTERM kita tangani halus dan keluar bersih
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

    # Windows: coba tangani event close/logoff/shutdown jika pywin32 ada
    try:
        import win32api  # type: ignore
        import win32con  # type: ignore
        def _win_handler(ctrl_type):
            # CTRL_CLOSE_EVENT / CTRL_LOGOFF_EVENT / CTRL_SHUTDOWN_EVENT
            _set_shutdown()
            # Beri waktu sebentar utk cleanup
            time.sleep(0.2)
            return True  # hindari force-kill
        win32api.SetConsoleCtrlHandler(_win_handler, True)
    except Exception:
        pass

def _atexit_cleanup():
    # Taruh hook tambahan kalau perlu (flush log dsb)
    pass

# ------------------------------ MAIN -------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(description="MINIPC/Local runner for SatpamLeina")
    parser.add_argument("--env", help="Path ke file env (override auto-detect)", default=None)
    parser.add_argument("--strict", action="store_true", help="Error bila env tidak ditemukan")
    parser.add_argument("--override", action="store_true", help="Timpa variabel env yang sudah ada")
    args = parser.parse_args(argv)

    _install_signal_handlers()
    atexit.register(_atexit_cleanup)

    env_path = find_env_file(args.env)
    if env_path and _is_readable_file(env_path):
        load_env_file(env_path, override=args.override)
        print(f"✅ Loaded env file: {os.path.basename(env_path)}")
    elif args.strict:
        print("❌ ENV tidak ditemukan. Set --env atau letakkan SatpamBot.env bersebelahan.", file=sys.stderr)
        sys.exit(2)
    else:
        print("ℹ️ ENV tidak ditemukan, lanjut tanpa load file (menggunakan os.environ saat ini).")

    # Jalankan entry lama tanpa diubah
    try:
        import main as _entry
    except Exception as e:
        print(f"❌ Gagal import main.py: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        _entry.main()
    except KeyboardInterrupt:
        # Tangkap agar tidak ada traceback panjang
        print("\n👋 Terima kasih. Shutting down gracefully…")
        sys.exit(0)
    except SystemExit as e:
        # Hargai exit code bila ada
        raise
    except Exception as e:
        # Laporkan error lain
        print(f"\n💥 Unhandled error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
