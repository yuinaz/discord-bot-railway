# Restart by exiting process (Render will auto-restart the service)
import os, sys, time
print("[selfheal] Restarting process now...", flush=True)
sys.stdout.flush()
time.sleep(0.2)
os._exit(0)
