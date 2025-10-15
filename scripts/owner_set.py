
#!/usr/bin/env python
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from satpambot.config.runtime import set_cfg
if len(sys.argv) < 2:
    print('Usage: python scripts/owner_set.py <discord_user_id>'); raise SystemExit(2)
set_cfg('OWNER_USER_ID', sys.argv[1])
print('OWNER_USER_ID set to', sys.argv[1])
