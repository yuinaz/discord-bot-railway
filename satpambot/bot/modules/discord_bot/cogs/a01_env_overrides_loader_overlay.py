
from discord.ext import commands
import os, json

def _flatten(d, prefix=""):
    flat = {}
    for k, v in d.items():
        kk = f"{prefix}{k}" if not prefix else f"{prefix}{k}"
        if isinstance(v, dict):
            flat.update(_flatten(v, prefix=kk + "_"))
        else:
            flat[kk] = v
    return flat

class EnvOverridesLoader(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        path = os.getenv("CONFIG_OVERRIDES_PATH", "data/config/overrides.json")
        alt = os.getenv("CONFIG_OVERRIDES_FALLBACK", "data/config/overrides.render-free.json")
        used = None
        for p in (path, alt):
            try:
                if not os.path.exists(p): continue
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # allow plain key->value or nested under 'env'
                envmap = data.get("env", data)
                # convert all values to str for os.environ
                cnt = 0
                for k, v in envmap.items():
                    if isinstance(v, (dict, list)):
                        v = json.dumps(v, ensure_ascii=False)
                    os.environ[str(k)] = str(v)
                    cnt += 1
                print(f"[env_overrides] loaded {cnt} keys from {p}")
                used = p
                break
            except Exception as e:
                print(f"[env_overrides] failed loading {p}: {e!r}")
        if not used:
            print("[env_overrides] no overrides file found (skip)")
async def setup(bot):
    await bot.add_cog(EnvOverridesLoader(bot))
    print("[env_overrides] overlay ready (CONFIG_OVERRIDES_PATH / overrides.json)")