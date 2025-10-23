import os, json, logging
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

DEFAULT_LADDER = {
    "SMP": {"L1": 2000, "L2": 4000, "L3": 6000},
    "SMA": {"L1": 4000, "L2": 7500, "L3": 9000},
    "KULIAH": {"S1": 19000, "S2": 35000, "S3": 58000, "S4": 70000, "S5": 96500, "S6": 158000, "S7": 220000, "S8": 262500}
}

class LadderAutoseed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task.start()

    def cog_unload(self):
        self._task.cancel()

    @tasks.loop(count=1)
    async def _task(self):
        url = os.getenv("UPSTASH_REST_URL") or os.getenv("UPSTASH_REDIS_REST_URL")
        tok = os.getenv("UPSTASH_REST_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN")
        if not (url and tok):
            return
        try:
            import httpx
        except Exception:
            log.info("[ladder_autoseed] httpx not available; skip")
            return

        ladder = DEFAULT_LADDER
        try:
            with open("data/neuro-lite/ladder.json", "r", encoding="utf-8") as f:
                ladder = json.load(f)
                for tier in ("SMP","SMA","KULIAH"):
                    ladder[tier] = ladder.get(tier, DEFAULT_LADDER[tier])
        except Exception:
            pass

        async with httpx.AsyncClient(timeout=5) as cli:
            headers = {"Authorization": f"Bearer {tok}"}
            async def hset(key, mapping):
                parts = []
                for k,v in mapping.items():
                    parts += [str(k), str(v)]
                path = "/".join(parts)
                return await cli.get(f"{url}/hset/{key}/{path}", headers=headers)
            async def rtype(key):
                r = await cli.get(f"{url}/type/{key}", headers=headers)
                return r.json().get("result")
            async def delete(key):
                await cli.get(f"{url}/del/{key}", headers=headers)

            for key, mapping in (("xp:ladder:SMP", ladder["SMP"]), ("xp:ladder:SMA", ladder["SMA"]), ("xp:ladder:KULIAH", ladder["KULIAH"])):
                try:
                    t = await rtype(key)
                    if t != "hash":
                        if t in ("string","list","set","zset","stream",None):
                            await delete(key)
                        await hset(key, mapping)
                        log.info("[ladder_autoseed] fixed %s -> hash fields=%d", key, len(mapping))
                except Exception:
                    log.warning("[ladder_autoseed] failed seed %s", key, exc_info=True)

    @_task.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(LadderAutoseed(bot))
