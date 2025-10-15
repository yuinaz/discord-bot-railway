# scripts/smoke_thread_safety.py
# Quick grep-like runtime validator for logs (to run AFTER bot starts for a bit)
import pathlib, re, sys
p = pathlib.Path("run.log")
if not p.exists():
    print("run.log not found. Start bot with tee run.log first.")
    sys.exit(0)
text = p.read_text(encoding="utf-8", errors="ignore")
ok_route = re.findall(r"memroute.*thread 1426397317598154844", text)
ok_protect = re.findall(r"thread_protect.*ids=.*1426397317598154844", text)
pinned = re.findall(r"pinned 'XP: Miner Memory' snapshot to channel 1426397317598154844", text)
print("RoutePatch:", "OK" if ok_route else "MISSING")
print("ThreadProtect:", "OK" if ok_protect else "MISSING")
print("Pinned XP to thread:", len(pinned))
