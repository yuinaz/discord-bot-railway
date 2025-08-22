#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def read(p: Path): return p.read_text(encoding="utf-8", errors="ignore")

cogs_dir = ROOT/'satpambot/bot/modules/discord_bot/cogs'
loader   = ROOT/'satpambot/bot/modules/discord_bot/cogs_loader.py'
dash     = ROOT/'satpambot/dashboard/app_dashboard.py'
fall     = ROOT/'satpambot/dashboard/app_fallback.py'

names = [p.name for p in cogs_dir.glob('*sticky*.py')]
print('== sticky ==')
print('found:', ', '.join(names) or '(none)')
m = re.search(r'DISABLED_COGS\s*=\s*set\(\(os\.getenv\("DISABLED_COGS"\)\s*or\s*"([^"]*)"\)\.split\(",\"\)\)\)', read(loader)) if loader.exists() else None
print('loader default:', m.group(1) if m else '(unknown)')
dup = len(names) >= 2 and not (m and all(x in m.group(1) for x in ('sticky_guard','status_sticky_patched')))
print('duplicate risk:', dup)

def has_filter(p: Path):
    s = read(p) if p.exists() else ''
    return bool(re.search(r"def\s+create_app\([^)]*\):[\s\S]{0,600}?_install_health_log_filter\(\)", s))

print('\n== healthz ==')
print('app_dashboard filter installed:', has_filter(dash))
print('app_fallback  filter installed:', has_filter(fall))
