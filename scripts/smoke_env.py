<<<<<<< HEAD
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
=======
import sys, platform
from importlib import metadata

def v(pkg, fallback=None):
    try:
        return metadata.version(pkg)
    except Exception as e:
        return f"ERR({e.__class__.__name__})" if fallback is None else fallback

print("=== ENV CHECK ===")
print(f"Python: {platform.python_version()} [{platform.system()}-{platform.version().split('.',1)[0]}]")
print(f"discord.py    : {v('discord.py')}")
print(f"flask         : {v('Flask')}")
print(f"aiohttp       : {v('aiohttp')}")
print(f"httpx         : {v('httpx')}")
print(f"groq          : {v('groq')}")
print(f"numpy         : {v('numpy')}")
print(f"psutil        : {v('psutil')}")
print(f"Pillow        : {v('Pillow')}")
print(f"tzdata        : {v('tzdata', 'bundled')}")
print(f"googletrans-py: {v('googletrans-py')}")
print(f"deep-translator: {v('deep-translator')}")
print(f"langdetect    : {v('langdetect')}")
print("== COMPAT CHECK: OK ==")
>>>>>>> ef940a8 (heal)
