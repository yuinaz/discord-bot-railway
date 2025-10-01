# main.py — startup logs preserved + backoff with early unban probe (no forcing)
import logging, threading, asyncio, time, re, pathlib
from app import app
from satpambot.bot.modules.discord_bot.shim_runner import start_bot
try:
    from satpambot.bot.modules.discord_bot.helpers import cf_login_guard as cfg
except Exception:
    cfg = None

log = logging.getLogger("entry.main")

def _run_web():
    log.info("🌐 Serving web on 0.0.0.0:10000")
    app.run(host="0.0.0.0", port=10000, debug=False, use_reloader=False)

def _should_backoff(exc: Exception) -> bool:
    s = f"{exc}"
    return ("429" in s) or ("1015" in s) or ("cloudflare" in s.lower())

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

def _force_paths():
    return [pathlib.Path('/data/force_login_now'), pathlib.Path('/tmp/force_login_now')]

def _check_force():
    for p in _force_paths():
        try:
            if p.exists():
                p.unlink(missing_ok=True)
                return True
        except Exception:
            pass
    return False

def main():
    logging.basicConfig(level=logging.INFO)
    t = threading.Thread(target=_run_web, name="web", daemon=True)
    t.start()
    log.info("Web is ready on port 10000")
    log.info("🤖 Starting Discord bot (shim_runner.start_bot)...")

    backoff = 10.0
    while True:
        try:
            asyncio.run(start_bot())
            return
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            if _should_backoff(e):
                ray, hint = _extract_ray_retry(e)
                wait = max(60.0, backoff)
                if cfg is not None:
                    try:
                        cfg.mark_429(ray_id=ray, retry_after_hint=hint)
                        wait = max(wait, cfg.suggested_sleep())
                    except Exception:
                        pass
                log.warning("Login blocked (%s). Backing off...", msg)
            else:
                wait = max(30.0, backoff)
                log.error("Bot crashed: %s", msg)

            # Wait loop with early-unban probe
            wait = min(1200.0, max(30.0, wait))
            deadline = time.time() + wait
            while True:
                remain = deadline - time.time()
                if remain <= 0:
                    break
                # probe every 10s (or 5s if < 1m left)
                step = 10.0 if remain > 60 else 5.0
                log.info("Restarting in %.1fs...", remain)
                # Early unban probe (no force). If ban gone, retry now.
                if cfg is not None:
                    try:
                        ok = cfg.probe_can_login(timeout=4.0)
                        if ok:
                            log.info("Unban detected by probe → retrying login now.")
                            break
                    except Exception:
                        pass
                # Manual force bypass (optional)
                if _check_force():
                    log.info("Force flag detected → retrying immediately.")
                    break
                time.sleep(min(step, remain))

            backoff = min(1200.0, max(backoff * 1.5, 60.0))

if __name__ == "__main__":
    main()
