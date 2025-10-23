# -*- coding: utf-8 -*-
"""
scripts/preflight_render_free.py (extended)
- Cek shim async: EmbedScribe.upsert & progress_embed_solo.update_embed
- Cek Upstash env + read xp keys (optional)
- Cek presence GROQ_API_KEY / GEMINI_API_KEY (sekadar peringatan)
Exit 0 selalu; hanya untuk log visibilitas.
"""
import os, importlib, inspect, json, sys

def check_upsert():
    m=importlib.import_module("satpambot.bot.utils.embed_scribe")
    ES=getattr(m,"EmbedScribe")
    up=getattr(ES,"upsert",None)
    return "async" if inspect.iscoroutinefunction(up) else ("shim" if up else "missing")

def check_progress_update():
    try:
        m=importlib.import_module("satpambot.bot.modules.discord_bot.cogs.progress_embed_solo")
    except Exception:
        return "n/a"
    fn=getattr(m,"update_embed",None)
    if not fn: return "missing"
    return "async" if inspect.iscoroutinefunction(fn) else "wrapped-or-sync"

def check_upstash():
    base=os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
    tok=os.getenv("UPSTASH_REDIS_REST_TOKEN","")
    if not base or not tok: return "env-missing"
    try:
        import urllib.request as r, json as j
        resp = r.urlopen(r.Request(f"{base}/get/xp:bot:senior_total", headers={"Authorization": f"Bearer {tok}"}), timeout=5)
        val = j.loads(resp.read().decode()).get("result")
        return f"ok:{val}"
    except Exception as e:
        return f"err:{e.__class__.__name__}"

def main():
    print("[preflight] upsert:", check_upsert())
    print("[preflight] progress_update:", check_progress_update())
    print("[preflight] upstash:", check_upstash())
    print("[preflight] groq:", "set" if os.getenv("GROQ_API_KEY") else "missing")
    print("[preflight] gemini:", "set" if os.getenv("GEMINI_API_KEY") else "missing")
    print("[preflight] OK")

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print("[preflight] WARN:", e)
        sys.exit(0)
