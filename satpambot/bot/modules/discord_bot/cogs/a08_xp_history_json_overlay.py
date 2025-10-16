import os
import json
import time
import asyncio
import logging
import inspect
from importlib import import_module

log = logging.getLogger(__name__)

_DEFAULTS = {
    "SINCE_DAYS": 7,
    "AWARD_PER_MESSAGE": 5,
    "SLEEP_MS": 350,
    "AUTHOR_COOLDOWN_SEC": 6,
    "CHANNEL_COOLDOWN_SEC": 2,
    "MAX_MESSAGES": 400,
    "MAX_PER_USER": 150,
    # Optional filter khusus channel tertentu (mis. QnA)
    # Contoh: [1426571542627614772]
    "CHANNEL_IDS": None,
}

def _load_local_config() -> dict:
    """
    Baca konfigurasi dari file JSON di dalam repo (tanpa ENV).
    Urutan prioritas:
      1) satpambot_config.local.json (root repo):
         - Bisa pakai blok "XP_HISTORY": {...}
         - atau flat keys "XP_HISTORY_*"
      2) satpambot/config/local.json (opsional fallback)
      3) _DEFAULTS
    """
    candidates = [
        os.path.join(os.getcwd(), "satpambot_config.local.json"),
        os.path.join(os.getcwd(), "satpambot", "config", "local.json"),
    ]
    cfg = dict(_DEFAULTS)
    for path in candidates:
        try:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                continue

            # Model 1: blok XP_HISTORY
            if isinstance(data.get("XP_HISTORY"), dict):
                block = data["XP_HISTORY"]
                for k, v in block.items():
                    kk = k.strip().upper()
                    if kk in _DEFAULTS:
                        cfg[kk] = v

            # Model 2: flat keys XP_HISTORY_*
            for k, v in list(data.items()):
                if isinstance(k, str) and k.upper().startswith("XP_HISTORY_"):
                    kk = k.upper().removeprefix("XP_HISTORY_")
                    if kk in _DEFAULTS:
                        cfg[kk] = v

            # Begitu ketemu satu file valid, berhenti
            break
        except Exception as e:
            log.warning("[xp_history_json_overlay] gagal baca %s: %r", path, e)
    return cfg

_CFG = _load_local_config()

def _wrap_award(fn, per_message: int, sleep_sec: float):
    """
    Wrapper generik untuk fungsi award (bisa async / sync). 
    Memastikan nilai XP per pesan minimal 'per_message' + jeda setelah award agar tidak 429.
    """
    if asyncio.iscoroutinefunction(fn):
        async def inner(*args, **kwargs):
            # set nilai minimal
            if "amount" in kwargs and isinstance(kwargs["amount"], (int, float)):
                kwargs["amount"] = max(int(kwargs["amount"]), int(per_message))
            else:
                # coba cari argumen numerik (biasanya di belakang)
                args = list(args)
                for i, a in enumerate(reversed(args)):
                    if isinstance(a, (int, float)):
                        idx = len(args) - 1 - i
                        args[idx] = max(int(a), int(per_message))
                        break
                args = tuple(args)
            try:
                return await fn(*args, **kwargs)
            finally:
                if sleep_sec > 0:
                    try:
                        await asyncio.sleep(sleep_sec)
                    except Exception:
                        pass
        return inner
    else:
        def inner(*args, **kwargs):
            if "amount" in kwargs and isinstance(kwargs["amount"], (int, float)):
                kwargs["amount"] = max(int(kwargs["amount"]), int(per_message))
            else:
                args = list(args)
                for i, a in enumerate(reversed(args)):
                    if isinstance(a, (int, float)):
                        idx = len(args) - 1 - i
                        args[idx] = max(int(a), int(per_message))
                        break
                args = tuple(args)
            try:
                return fn(*args, **kwargs)
            finally:
                if sleep_sec > 0:
                    try:
                        time.sleep(sleep_sec)
                    except Exception:
                        pass
        return inner

def _try_setattr(mod, name, value):
    if hasattr(mod, name):
        try:
            setattr(mod, name, value)
            log.info("[xp_history_json_overlay] set %s = %r", name, value)
            return True
        except Exception as e:
            log.warning("[xp_history_json_overlay] gagal set %s: %r", name, e)
    return False

def setup(bot):
    """
    Overlay ini tidak menambah cog baru; hanya memodifikasi perilaku xp_history_autocatchup
    menggunakan konfigurasi dari JSON internal repo.
    """
    try:
        mod = import_module("satpambot.bot.modules.discord_bot.cogs.xp_history_autocatchup")
    except Exception as e:
        log.error("[xp_history_json_overlay] tidak bisa import xp_history_autocatchup: %r", e)
        return

    # 1) Tuning konstanta (jika modul menyediakan)
    _try_setattr(mod, "LOOKBACK_HOURS", int(_CFG["SINCE_DAYS"]) * 24)
    _try_setattr(mod, "AUTHOR_COOLDOWN_SEC", int(_CFG["AUTHOR_COOLDOWN_SEC"]))
    _try_setattr(mod, "CHANNEL_COOLDOWN_SEC", int(_CFG["CHANNEL_COOLDOWN_SEC"]))
    _try_setattr(mod, "MAX_MESSAGES", int(_CFG["MAX_MESSAGES"]))
    _try_setattr(mod, "MAX_PER_USER", int(_CFG["MAX_PER_USER"]))

    # 2) Filter channel optional
    channel_ids = None
    if _CFG.get("CHANNEL_IDS"):
        try:
            # Normalisasi jadi set of int
            channel_ids = set(int(x) for x in _CFG["CHANNEL_IDS"])
        except Exception:
            channel_ids = None

    for varname in ("TARGET_CHANNEL_IDS", "CHANNEL_IDS", "XP_CHANNEL_IDS", "QNA_CHANNEL_IDS"):
        if channel_ids and hasattr(mod, varname):
            try:
                setattr(mod, varname, set(channel_ids))
                log.info("[xp_history_json_overlay] set %s = %r", varname, sorted(channel_ids))
            except Exception as e:
                log.warning("[xp_history_json_overlay] gagal set %s: %r", varname, e)

    # 3) Patch fungsi award historis agar minimal per_message + delay untuk hindari 429
    per_message = int(_CFG["AWARD_PER_MESSAGE"])
    sleep_sec = max(0.0, float(_CFG["SLEEP_MS"]) / 1000.0)
    patched = 0

    # a) module-level _award
    if hasattr(mod, "_award"):
        try:
            mod._award = _wrap_award(mod._award, per_message, sleep_sec)
            patched += 1
        except Exception as e:
            log.warning("[xp_history_json_overlay] gagal patch mod._award: %r", e)

    # b) cari class dengan method _award / award
    try:
        for name in dir(mod):
            obj = getattr(mod, name, None)
            if inspect.isclass(obj):
                for mname in ("_award", "award"):
                    if hasattr(obj, mname):
                        try:
                            orig = getattr(obj, mname)
                            setattr(obj, mname, _wrap_award(orig, per_message, sleep_sec))
                            patched += 1
                        except Exception as e:
                            log.warning("[xp_history_json_overlay] gagal patch %s.%s: %r", name, mname, e)
    except Exception as e:
        log.warning("[xp_history_json_overlay] iter class error: %r", e)

    log.info(
        "[xp_history_json_overlay] patched_award=%s per_message=%s sleep_ms=%s lookback_days=%s channels=%s",
        patched, per_message, int(_CFG["SLEEP_MS"]), int(_CFG["SINCE_DAYS"]), (sorted(channel_ids) if channel_ids else None),
    )
