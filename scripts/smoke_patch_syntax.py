#!/usr/bin/env python3
import py_compile, sys
paths = [
  "satpambot/ai/persona_injector.py",
  "satpambot/bot/modules/discord_bot/cogs/neuro_autolearn_moderated_v2.py",
  "satpambot/bot/modules/discord_bot/cogs/a09_work_xp_overlay.py",
  "satpambot/bot/modules/discord_bot/cogs/a27_phase_transition_overlay.py",
]
for p in paths:
    try:
        py_compile.compile(p, doraise=True)
        print("[OK]", p)
    except Exception as e:
        print("[FAIL]", p, e); sys.exit(1)
print("SMOKE_SYNTAX_OK")
