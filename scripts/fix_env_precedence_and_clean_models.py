# scripts/fix_env_precedence_and_clean_models.py
"""
- Switch precedence to ENV > LOCAL > DEFAULTS (requires patched runtime.py).
- Remove stale keys that force GPT-5 mini in satpambot_config.local.json.
Usage:
    python -m scripts.fix_env_precedence_and_clean_models
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "satpambot_config.local.json"

STALE_KEYS = ["OPENAI_CHAT_MODEL", "CHAT_MODEL", "OPENAI_TIMEOUT_S"]

def main():
    if not CFG.exists():
        print("No local config file to clean:", CFG)
        return
    data = json.loads(CFG.read_text(encoding="utf-8") or "{}")
    changed = False
    for k in STALE_KEYS:
        if k in data:
            data.pop(k)
            changed = True
    if changed:
        tmp = CFG.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(CFG)
        print("Cleaned keys:", ", ".join(STALE_KEYS))
    else:
        print("No stale keys found.")

if __name__ == "__main__":
    main()
