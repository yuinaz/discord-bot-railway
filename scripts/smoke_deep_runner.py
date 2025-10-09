#!/usr/bin/env python
# smoke_deep_runner: run smoke_deep.py with a safe sys.path bootstrap.
# Usage:
#   python scripts/smoke_deep_runner.py

import runpy
import sys
from pathlib import Path

# Ensure project root (parent of /scripts) is on sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

target = SCRIPTS_DIR / "smoke_deep.py"
if not target.exists():
    sys.stderr.write(f"[runner] smoke_deep.py not found at {target}\n")
    sys.exit(1)

# Execute smoke_deep.py as a script, preserving its __main__ behavior
runpy.run_path(str(target), run_name="__main__")
