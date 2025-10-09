
Unified Patch v6 — JSON configs + fixed smoketests + shadow/progress/dupe/CF guards

1) Extract to repo root (so 'satpambot/...' and 'scripts/...' align).
2) Edit 'satpambot_config.local.json' at repo root (copy is also provided in /config and /data/config).
3) Run smoke:
     python scripts/smoketest_all.py
     python scripts/smoke_deep.py

Notes:
- 'scripts/__init__.py' included so 'from scripts.smoke_utils import ...' works.
- smoketests push project root + scripts to sys.path; fixes ModuleNotFoundError.
- All JSON templates included, plus data skeletons (neuro-lite state, phash db, embed_scribe state).
- Background loops honor SMOKE_MODE (true disables loops during tests).
