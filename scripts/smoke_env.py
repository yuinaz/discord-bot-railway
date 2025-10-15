import os, sys
try:
    from satpambot.config.runtime import cfg  # type: ignore
except Exception:
    def cfg(k, default=None): return os.getenv(k, default)
keys = ["GEMINI_API_KEY","GROQ_API_KEY","DISCORD_TOKEN"]
print("== SatpamBot env check ==")
missing = []
for k in keys:
    v = cfg(k) or os.getenv(k)
    print(f"{k} =>", "OK" if v else "MISSING")
    if not v: missing.append(k)
if not any(os.path.exists(p) for p in ["satpambot_config.local.json","config/satpambot_config.local.json"]):
    print("[hint] Buat satpambot_config.local.json dari satpambot_config.local.example.json")
sys.exit(0 if not missing else 1)
