
#!/usr/bin/env python
import sys
from pathlib import Path

# Ensure repo root (one level up from scripts/) is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
import sys as _sys
if str(REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(REPO_ROOT))

from satpambot.config.env_importer import parse_dotenv, import_env_map, file_sha256
from satpambot.config.runtime import set_cfg

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'SatpamBot.env'
    data = parse_dotenv(path)
    if not data:
        print(f"[import] No vars loaded from {path} (file missing or empty)")
        raise SystemExit(1)
    c_cfg, c_sec, skipped, cfg_keys, sec_keys = import_env_map(data)
    sha = file_sha256(path)
    set_cfg('IMPORTED_ENV_SHA_SATPAMBOT', sha)
    set_cfg('IMPORTED_ENV_FILE', path)
    set_cfg('IMPORTED_ENV_LAST_CFG', int(c_cfg))
    set_cfg('IMPORTED_ENV_LAST_SEC', int(c_sec))
    set_cfg('IMPORTED_ENV_LAST_CFG_KEYS', cfg_keys[:40])
    set_cfg('IMPORTED_ENV_LAST_SEC_KEYS', sec_keys[:40])
    set_cfg('IMPORTED_ENV_NOTIFY', True)
    print(f"[import] Imported from {path}: config={c_cfg}, secrets={c_sec}, skipped={skipped}")
    print("[import] Done. Stored in satpambot_config.local.json (and secrets map).\n        DM import report will be sent on next bot startup.")

if __name__ == '__main__':
    main()
