from __future__ import annotations

# scripts/enforce_diet_dm_runtime.py
"""
Set default flags to minimize DM noise.
"""
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
    # diet defaults
    data.setdefault("AUTO_UPDATE_PROPOSAL_DM", False)
    data.setdefault("AUTO_UPDATE_CRITICAL_ONLY", True)
    data.setdefault("IMPORTED_ENV_NOTIFY", False)
    data.setdefault("CHAT_AUTOCONFIG_NOTIFY", False)
    CFG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[OK] diet DM flags enforced in satpambot_config.local.json")

if __name__ == "__main__":
    main()
