# main.py — exact startup logs + safe login backoff (no config change)
import logging, threading, asyncio, time, re
from app import app
from satpambot.bot.modules.discord_bot.shim_runner import start_bot
try:
    from satpambot.bot.modules.discord_bot.helpers import cf_login_guard as cfg
except Exception:  # fallback if helper not present
    cfg = None

log = logging.getLogger("entry.main")

def _run_web():
    log.info("🌐 Serving web on 0.0.0.0:10000")
    app.run(host="0.0.0.0", port=10000, debug=False, use_reloader=False)

def _should_backoff(exc: Exception) -> bool:
    s = f"{exc}"
    return ("429" in s) or ("Error 1015" in s) or ("cloudflare" in s.lower())

def _extract_ray_retry(exc: Exception):
    s = f"{exc}"
    ray, hint = None, None
    m = re.search(r"Ray ID:\s*([0-9a-fA-F]+)", s)
    if m: ray = m.group(1)
    m2 = re.search(r"Retry-After:\s*([0-9.]+)", s, re.I)
    if m2:
        try: hint = float(m2.group(1))
        except Exception: pass
    return ray, hint

def main():
    logging.basicConfig(level=logging.INFO)
    # EXACT header lines you require:
    t = threading.Thread(target=_run_web, name="web", daemon=True)
    t.start()
    log.info("Web is ready on port 10000")
    log.info("🤖 Starting Discord bot (shim_runner.start_bot)...")

    # Backoff loop (only triggers if login throws 429/1015)
    backoff = 10.0
    while True:
        try:
            asyncio.run(start_bot())
            return
        except Exception as e:
            if _should_backoff(e):
                ray, hint = _extract_ray_retry(e)
                if cfg is not None:
                    try:
                        cfg.mark_429(ray_id=ray, retry_after_hint=hint)
                        wait = max(backoff, cfg.suggested_sleep())
                    except Exception:
                        wait = max(60.0, backoff)
                else:
                    wait = max(60.0, backoff)
            else:
                wait = max(30.0, backoff)
            log.error("Bot crashed: %s", e, exc_info=True)
            log.info("Restarting in %.1fs...", min(900.0, wait))
            time.sleep(min(900.0, wait))
            backoff = min(900.0, max(backoff * 1.5, 60.0))

if __name__ == "__main__":
    main()
