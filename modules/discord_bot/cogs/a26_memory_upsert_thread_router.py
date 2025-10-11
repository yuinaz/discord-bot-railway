# a26_memory_upsert_thread_router.py
import logging, importlib
log=logging.getLogger(__name__)
def _get_curriculum_thread_id():
    try:
        a20=importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd")
        cfg=a20._load_cfg(); cid=cfg.get("report_channel_id")
        return int(cid) if cid else None
    except Exception as e:
        log.debug("[memroute] cannot read curriculum.report_channel_id: %r", e); return None
def _is_curriculum_snapshot(payload):
    title=(payload or {}).get("title") or ""; tl=title.lower().strip()
    if tl.startswith("xp:"): return True
    if "curriculum" in tl or "tk→sd" in tl or "tk->sd" in tl: return True
    tag=(payload or {}).get("tag") or (payload or {}).get("scope") or ""
    if isinstance(tag,str) and tag.lower() in ("curriculum","miner_xp","xp_snapshot"): return True
    return False
try:
    mem=importlib.import_module("satpambot.bot.modules.discord_bot.helpers.memory_upsert")
    original=getattr(mem,"upsert_pinned_memory",None)
    if original is None:
        log.warning("[memroute] helpers.memory_upsert.upsert_pinned_memory not found; skip patch")
    else:
        import inspect
        async def _patched(*args, **kwargs):
            bot=None; payload=None; rest=()
            if args:
                if hasattr(args[0],"loop") or hasattr(args[0],"add_view"):
                    bot=args[0]
                    if len(args)>=2 and isinstance(args[1],dict): payload=dict(args[1]); rest=args[2:]
                    else: rest=args[1:]
                elif isinstance(args[0],dict): payload=dict(args[0]); rest=args[1:]
                else: rest=args[1:]
            if payload is None: payload=dict(kwargs.get("payload") or {})
            target_thread=_get_curriculum_thread_id()
            if target_thread and _is_curriculum_snapshot(payload):
                payload["channel_id"]=int(target_thread); kwargs["payload"]=payload
                log.info("[memroute] routing pinned memory '%s' -> thread %s",(payload.get("title") or "")[:60], target_thread)
            if bot is not None: return await original(bot, *(rest or ()), **kwargs)
            else:
                if inspect.iscoroutinefunction(original): return await original(*(rest or ()), **kwargs)
                else: return original(*(rest or ()), **kwargs)
        setattr(mem,"upsert_pinned_memory",_patched); log.info("[memroute] upsert_pinned_memory patched for targeted thread routing")
except Exception: log.warning("[memroute] failed to apply patch", exc_info=True)
async def setup(bot): return
