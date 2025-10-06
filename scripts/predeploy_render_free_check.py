import os, sys, sqlite3, traceback, importlib, asyncio, time
from pathlib import Path

# --- Ensure repo root is on sys.path even when this file is run from scripts/ ---
THIS = Path(__file__).resolve()
REPO_ROOT = THIS.parents[1]  # <repo>/
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FAIL = 0

def step(name):
    print(f"== {name} ==")

def ok(msg): print("OK  :", msg)
def fail(msg):
    global FAIL
    print("FAIL:", msg)
    FAIL += 1

def check_env_profile():
    step("env profile (lite by default)")
    try:
        envcfg = importlib.import_module("satpambot.bot.config.envcfg")
        soft, hard = envcfg.memory_thresholds_mb()
        ok(f"memory thresholds soft={soft}MB hard={hard}MB")
        if hard <= soft:
            fail("hard must be > soft")
    except Exception as e:
        traceback.print_exc()
        fail("env profile failed")

def check_sql_exec():
    step("sticker_learner SQL exec")
    try:
        os.environ.setdefault("NEUROLITE_MEMORY_DB", os.path.join("data","preflight.sqlite3"))
        slmod = importlib.import_module("satpambot.bot.modules.discord_bot.helpers.sticker_learner")
        SL = getattr(slmod, "StickerLearner")
        sl = SL()
        sl.log_event(1, "happy", True, True, 0, False, False, {"exclam":1,"www":1,"wkwk":0,"lol":0})
        ok("insert events/stats executed")
    except Exception as e:
        traceback.print_exc()
        fail("sticker_learner SQL failed")

def check_fake_runtime():
    step("fake Discord runtime (load cogs)")
    try:
        # Run the helper by absolute path so it works without package import for 'scripts'
        from runpy import run_path
        helper = REPO_ROOT / "scripts" / "test_fake_discord_runtime.py"
        if not helper.exists():
            fail(f"helper not found: {helper}")
            return
        run_path(str(helper), run_name="__main__")
        ok("cogs setup on FakeBot OK")
    except Exception as e:
        traceback.print_exc()
        fail("fake runtime failed")

def main():
    check_env_profile()
    check_sql_exec()
    check_fake_runtime()

    print("\n=== PREDEPLOY SUMMARY ===")
    if FAIL == 0:
        print("PASS")
        sys.exit(0)
    else:
        print(f"FAILED checks: {FAIL}")
        sys.exit(1)

if __name__ == "__main__":
    main()
