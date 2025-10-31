#!/usr/bin/env python3
# Offline QnA readiness smoke (no network, no Discord login)
import json, os, re, sys, py_compile, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
OVR = ROOT / "data" / "config" / "overrides.render-free.json"
COGS = ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs"

def ok(x): return f"[OK]  {x}"
def warn(x): return f"[WARN]{x}"
def fail(x): return f"[FAIL]{x}"

def load_overrides():
    if not OVR.is_file():
        print(fail(f"missing {OVR}")); return {}
    try:
        return json.loads(OVR.read_text(encoding="utf-8"))
    except Exception as e:
        print(fail(f"parse overrides: {e}")); return {}

def show_qna_env(env):
    qna_enable = str(env.get("QNA_ENABLE", "0"))
    ch_id = str(env.get("QNA_CHANNEL_ID", "")).strip()
    interval = str(env.get("QNA_INTERVAL_SEC", "NA"))
    gem_model = env.get("LLM_GEMINI_MODEL") or env.get("GEMINI_MODEL") or "NA"
    groq_model = env.get("LLM_GROQ_MODEL") or env.get("GROQ_MODEL") or "NA"

    print("==[QNA env]==")
    print(ok(f"QNA_ENABLE={qna_enable}")) if qna_enable=="1" else print(warn(f"QNA_ENABLE={qna_enable}"))
    # validate channel id: only digits, 10-20 length
    ch_clean = ch_id.strip().strip('"').strip("'").replace("\\","")
    if re.fullmatch(r"\d{10,22}", ch_clean):
        if ch_id!=ch_clean:
            print(warn(f"QNA_CHANNEL_ID has stray quotes/escapes -> normalized '{ch_clean}'"))
        else:
            print(ok(f"QNA_CHANNEL_ID={ch_clean}"))
    else:
        print(fail(f"QNA_CHANNEL_ID invalid -> '{ch_id}'"))
    # interval
    try:
        ival = int(interval)
        if ival>=60:
            print(ok(f"QNA_INTERVAL_SEC={ival}"))
        else:
            print(warn(f"QNA_INTERVAL_SEC too small -> {ival}"))
    except Exception:
        print(fail(f"QNA_INTERVAL_SEC invalid -> '{interval}'"))
    # models
    print(ok(f"LLM_GEMINI_MODEL={gem_model}"))
    print(ok(f"LLM_GROQ_MODEL={groq_model}"))

def compile_if_exists(path):
    try:
        py_compile.compile(str(path), doraise=True)
        print(ok(f"compile {path.relative_to(ROOT)}"))
        return True
    except Exception as e:
        print(fail(f"compile {path.relative_to(ROOT)}: {e}"))
        return False

def grep_embed_titles(a24_path):
    t = a24_path.read_text(encoding="utf-8", errors="ignore")
    p1 = re.search(r'QNA_EMBED_TITLE_PROVIDER\s*=\s*(.+)', t)
    p2 = re.search(r'QNA_EMBED_TITLE_LEINA\s*=\s*(.+)', t)
    print("==[a24 embed titles]==")
    if p1: print(ok("PROVIDER -> "+p1.group(1).strip()))
    else: print(warn("QNA_EMBED_TITLE_PROVIDER not found"))
    if p2: print(ok("LEINA    -> "+p2.group(1).strip()))
    else: print(warn("QNA_EMBED_TITLE_LEINA not found"))
    # check provider string contains {provider}
    if p1 and "{provider}" not in p1.group(1):
        print(warn("Provider title does not contain {provider}"))

def check_scheduler():
    sch = COGS/"a24_qna_autolearn_scheduler.py"
    print("==[scheduler]==")
    if not sch.is_file():
        print(warn("a24_qna_autolearn_scheduler.py not found"))
        return
    t = sch.read_text(encoding="utf-8", errors="ignore")
    # must use QNA_CHANNEL_ID (not QNA_ISOLATED_ID)
    uses = "QNA_CHANNEL_ID" in t
    if uses: print(ok("uses QNA_CHANNEL_ID"))
    else: print(fail("scheduler does not reference QNA_CHANNEL_ID"))
    compile_if_exists(sch)

def main():
    print("====== QNA OFFLINE SMOKE ======")
    # cogs presence
    a24 = COGS/"a24_qna_auto_answer_overlay.py"
    a06 = COGS/"a06_autolearn_qna_answer_overlay.py"
    a06_off = COGS/"a06_autolearn_qna_answer_overlay.py.off"
    print("==[cogs]==")
    print(ok("a24_qna_auto_answer_overlay.py present")) if a24.is_file() else print(fail("a24 missing"))
    if a06_off.is_file():
        print(ok("a06 is OFF (.off)"))
    else:
        print(((warn("a06 ACTIVE"))) if a06.is_file() else ok("a06 not present"))

    # compile a24 (and a06 if active)
    if a24.is_file(): compile_if_exists(a24)
    if a06.is_file(): compile_if_exists(a06)

    # overrides env
    ov = load_overrides()
    env = ov.get("env", {})
    show_qna_env(env)

    # embed titles
    if a24.is_file(): grep_embed_titles(a24)

    # scheduler
    check_scheduler()

    print("====== DONE ======")

if __name__ == "__main__":
    sys.exit(main())
