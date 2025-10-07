
# sitecustomize: auto-import SatpamBot.env into internal config on startup,
# and persist an import report for the DM embed.
import os
from satpambot.config.env_importer import parse_dotenv, import_env_map, file_sha256
from satpambot.config.runtime import cfg, set_cfg

ENV_FILE = os.getenv('SATPAMBOT_ENV_PATH', 'SatpamBot.env')

def _auto_import():
    try:
        sha = file_sha256(ENV_FILE)
        if not sha:
            return
        last = cfg('IMPORTED_ENV_SHA_SATPAMBOT')
        if last == sha:
            return  # already imported this revision
        data = parse_dotenv(ENV_FILE)
        if not data:
            return
        c_cfg, c_sec, skipped, cfg_keys, sec_keys = import_env_map(data)
        # Persist metadata for reporter cog
        set_cfg('IMPORTED_ENV_SHA_SATPAMBOT', sha)
        set_cfg('IMPORTED_ENV_FILE', ENV_FILE)
        set_cfg('IMPORTED_ENV_LAST_CFG', int(c_cfg))
        set_cfg('IMPORTED_ENV_LAST_SEC', int(c_sec))
        # keep only first 40 keys to avoid bloat
        set_cfg('IMPORTED_ENV_LAST_CFG_KEYS', cfg_keys[:40])
        set_cfg('IMPORTED_ENV_LAST_SEC_KEYS', sec_keys[:40])
        set_cfg('IMPORTED_ENV_NOTIFY', True)
        print(f"[sitecustomize] Imported {c_cfg} config keys, {c_sec} secrets from {ENV_FILE}.")
    except Exception as e:
        print(f"[sitecustomize] env import failed: {e}")

_auto_import()
