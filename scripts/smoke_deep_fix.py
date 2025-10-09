
#!/usr/bin/env python3
import sys, os, subprocess

here = os.path.abspath(os.path.dirname(__file__))
repo = os.path.abspath(os.path.join(here, ".."))
if repo not in sys.path: sys.path.insert(0, repo)

# Reuse the patched smoke_deep
from scripts.smoke_deep import main as _main

if __name__ == "__main__":
    _main()
