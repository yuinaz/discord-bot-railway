from __future__ import annotations

# scripts/set_selfheal_thread_defaults.py
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "satpambot_config.local.json"

def main():
    data = {}
    if CFG.exists():
        try:
            data = json.loads(CFG.read_text(encoding='utf-8'))
        except Exception:
            data = {}
    data.setdefault("SELFHEAL_THREAD_NAME", "repair and update log")
    # LOG_CHANNEL_ID_RAW harus sudah di-set; kalau belum, biarkan alur pencarian by name
    CFG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print("[OK] Set SELFHEAL_THREAD_NAME=repair and update log (and left LOG_CHANNEL_ID_RAW as-is).")

if __name__ == "__main__":
    main()
