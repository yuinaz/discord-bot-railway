
import os, json, re, sys
from pathlib import Path

ENV_FILE = Path("SatpamBot.env")
OUT_FILE = Path("satpambot/config/99_env_override.json")

def parse_env_line(line: str):
    line = line.strip()
    if not line or line.startswith("#"): 
        return None, None
    if "=" not in line:
        return None, None
    k, v = line.split("=", 1)
    return k.strip(), v.strip()

def main():
    if not ENV_FILE.exists():
        print(f"[ERR] {ENV_FILE} tidak ditemukan. Taruh SatpamBot.env di ROOT repo.")
        sys.exit(1)

    data = {}
    for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        k, v = parse_env_line(line)
        if not k:
            continue
        # strip quotes
        if v.startswith(("'", '"')) and v.endswith(("'", '"')) and len(v) >= 2:
            v = v[1:-1]
        data[k] = v

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] ENV diimpor ke {OUT_FILE} ({len(data)} keys).")
    print("[NOTE] File ini sudah seharusnya UNTRACKED. Pastikan .gitignore memuatnya.")

if __name__ == "__main__":
    main()
