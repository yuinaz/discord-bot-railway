#!/usr/bin/env python
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from satpambot.config.runtime import set_cfg

defaults = {
    'CHAT_ENABLE': True,
    'CHAT_ALLOW_DM': True,
    'CHAT_ALLOW_GUILD': True,
    'CHAT_MENTIONS_ONLY': False,
    'CHAT_MIN_INTERVAL_S': 8,
    'OPENAI_CHAT_MODEL': 'gpt-5-mini',
    'CHAT_MODEL': 'gpt-5-mini',
    'CHAT_MAX_TOKENS': 256,
    'OPENAI_TIMEOUT_S': 20,
}
for k, v in defaults.items():
    set_cfg(k, v)
print('Applied:', ', '.join(defaults.keys()))
