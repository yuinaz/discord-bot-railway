#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoketest: SelfLearning (v4)
- Verifies module import for self_learning_guard
- Does not modify configs
"""
import importlib, os, sys, traceback

def repo_root() -> str:
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, ".."))

def main() -> int:
    root = repo_root()
    if root not in sys.path:
        sys.path.insert(0, root)

    MOD = "satpambot.bot.modules.discord_bot.cogs.self_learning_guard"
    try:
        importlib.import_module(MOD)
        print(f"OK   : import OK: {MOD}")
        return 0
    except Exception as e:
        print(f"FAIL : {MOD}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
