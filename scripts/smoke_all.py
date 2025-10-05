#!/usr/bin/env python3



# -*- coding: utf-8 -*-



from __future__ import annotations

import importlib
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))



SCRIPTS = os.path.join(ROOT, "scripts")



PATCHES = os.path.join(ROOT, "patches")







# Ensure repo root (the folder that contains 'satpambot/') is importable



if ROOT not in sys.path:



    sys.path.insert(0, ROOT)











def run_cmd(args):



    print(f"$ {' '.join(args)}")



    p = subprocess.run(args, capture_output=True, text=True)



    if p.stdout:



        print(p.stdout.rstrip())



    if p.stderr:



        print(p.stderr.rstrip(), file=sys.stderr)



    return p.returncode == 0











def try_import(modname):



    try:



        importlib.invalidate_caches()



        importlib.import_module(modname)



        print(f"OK   : import {modname}")



        return True



    except Exception as e:



        print(f"FAILED import {modname}: {e}")



        return False











def run_lint(strict: bool = False) -> bool:



    # Run linter (ruff preferred, fallback to flake8).



    # - strict=False: do not fail the smoke even if lint fails (WARN only)



    # - strict=True : fail the smoke when lint returns non-zero



    tools = [



        [sys.executable, "-m", "ruff", "check", ROOT],



        [sys.executable, "-m", "flake8", ROOT],



    ]



    any_run = False



    for args in tools:



        tool_name = args[2] if len(args) > 2 else "tool"



        print(f"== Lint: {' '.join(args)} ==")



        try:



            p = subprocess.run(args)



            any_run = True



            if p.returncode == 0:



                print("Lint OK")



                return True



            else:



                if strict:



                    print("Lint FAIL (strict mode)")



                    return False



                else:



                    print("Lint WARN (non-strict) — continuing")



                    return True



        except FileNotFoundError:



            print(f"{tool_name} not found, trying next...")



            continue



    if not any_run:



        print("Lint SKIP (ruff/flake8 not installed)")



    return True











def main():



    py = sys.executable



    ok = True



    print("== Smoke: all ==")







    # Optional strict lint mode



    strict_lint = "--strict-lint" in sys.argv







    sc = os.path.join(SCRIPTS, "smoke_cogs.py")



    if os.path.exists(sc):



        ok = run_cmd([py, sc]) and ok



    else:



        print("SKIP : scripts/smoke_cogs.py tidak ditemukan")







    # Self-learning smoketest (pick the newest we find)



    cand = [



        "smoketest_self_learning_v4.py",



        "smoketest_self_learning_v3.py",



        "smoketest_self_learning_v2.py",



        "smoketest_self_learning.py",



    ]



    chosen = None



    for c in cand:



        p = os.path.join(SCRIPTS, c)



        if os.path.exists(p):



            chosen = p



            break



    if chosen:



        print(f"== self-learning :: {os.path.basename(chosen)} ==")



        ok = run_cmd([py, chosen]) and ok



    else:



        print("SKIP : smoketest_self_learning_* tidak ditemukan")







    # Auto-inject guard hooks (optional)



    if "--inject" in sys.argv:



        inj = os.path.join(PATCHES, "auto_inject_guard_hooks.py")



        if os.path.exists(inj):



            print("== auto-inject guard hooks ==")



            ok = run_cmd([py, inj]) and ok



        else:



            print("SKIP : patches/auto_inject_guard_hooks.py tidak ditemukan")







    # Lint step (non-strict by default)



    print("== lint check ==")



    ok = run_lint(strict=strict_lint) and ok







    print("== import checks ==")



    ok = try_import("satpambot.ml.guard_hooks") and ok



    ok = try_import("satpambot.bot.modules.discord_bot.cogs.self_learning_guard") and ok







    print("\n== Summary ==")



    print("PASS" if ok else "FAIL")



    sys.exit(0 if ok else 1)











if __name__ == "__main__":



    main()



