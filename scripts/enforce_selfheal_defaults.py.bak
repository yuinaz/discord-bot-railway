from __future__ import annotations

# scripts/enforce_selfheal_defaults.py
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "satpambot_config.local.json"

def main():
    data = {}
    if CFG.exists():
        try:
            data = json.loads(CFG.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.setdefault("SELFHEAL_ENABLE", True)
    data.setdefault("SELFHEAL_ANALYZE_INTERVAL_S", 600)
    data.setdefault("SELFHEAL_AUTO_APPLY_SAFE", True)
    data.setdefault("SELFHEAL_MAX_ACTIONS_PER_HOUR", 3)
    data.setdefault("SELFHEAL_DM_SUMMARY", False)
    data.setdefault("SELFHEAL_ALLOWED_ACTIONS", "set_cfg,reload_extension,send_log")
    CFG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[OK] Self-Heal defaults enforced.")

if __name__ == "__main__":
    main()
