
import os, sys
prov = os.getenv("AI_PROVIDER", "").lower()
gkey = os.getenv("GROQ_API_KEY")
print(f"[info] AI_PROVIDER={prov!r}")
if prov != "groq":
    print("[WARN] Set AI_PROVIDER=groq in SatpamBot.env lalu jalankan scripts/env_to_config.py")
    sys.exit(0)
if not gkey:
    print("[ERR] Missing GROQ_API_KEY in environment (SatpamBot.env).")
    sys.exit(2)
try:
    from openai import OpenAI
except Exception as e:
    print("[ERR] library 'openai' belum terpasang:", e); sys.exit(3)
client = OpenAI(api_key=gkey, base_url="https://api.groq.com/openai/v1")
# do a lightweight models list
try:
    models = client.models.list()
    names = [m.id for m in models.data][:5]
    print("[OK] Groq reachable. Example models:", ", ".join(names) or "(none)")
    sys.exit(0)
except Exception as e:
    print("[ERR] ping Groq gagal:", e); sys.exit(4)
