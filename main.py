# main.py — integrate CF login guard to prevent restart loops on 429/1015
import asyncio, logging, time, sys, re
from satpambot.bot.modules.discord_bot.shim_runner import start_bot
from satpambot.bot.modules.discord_bot.helpers import cf_login_guard as cfg

log = logging.getLogger("entry.main")

_RAY_RE = re.compile(r"Ray ID:\s*([0-9a-fA-F]+)")
_RETRY_AFTER_RE = re.compile(r"Retry-After:\s*([0-9.]+)", re.I)

async def _bot_once_async():
    wait = cfg.suggested_sleep()
    if wait > 0:
        log.warning("⏳ Login delayed by cf_login_guard: sleeping %.1fs before trying...", wait)
        await asyncio.sleep(wait)

    log.info("🤖 Starting Discord bot (shim_runner.start_bot)...")
    await start_bot()

def main():
    backoff = 10.0
    while True:
        try:
            # Fresh loop every cycle
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_bot_once_async())
            break
        except Exception as e:
            emsg = f"{e}"
            is429 = ("429" in emsg) or ("Error 1015" in emsg) or ("cloudflare" in emsg.lower())
            if is429:
                # Extract Ray ID if present and Retry-After if any (best-effort)
                ray = None
                try:
                    m = _RAY_RE.search(emsg)
                    if m: ray = m.group(1)
                except Exception: pass
                retry_hint = None
                try:
                    m2 = _RETRY_AFTER_RE.search(emsg)
                    if m2: retry_hint = float(m2.group(1))
                except Exception: pass
                cfg.mark_429(ray_id=ray, retry_after_hint=retry_hint)
                backoff = max(backoff, cfg.suggested_sleep())
            log.error("Bot crashed: %s", e, exc_info=True)
        finally:
            try:
                if not loop.is_closed():
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    loop.close()
            except Exception:
                pass
        # Apply backoff (jitter) before retry; cap to 15 minutes
        jitter = min(30.0, backoff * 0.1)
        sleep_for = min(900.0, max(10.0, backoff) + (jitter if jitter>0 else 0.0))
        log.info("Restarting in %.1fs...", sleep_for)
        time.sleep(sleep_for)
        backoff = min(900.0, max(backoff * 1.5, 60.0))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log.info("🌐 Serving web on 0.0.0.0:10000")
    main()
