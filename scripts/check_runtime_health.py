
import re
from pathlib import Path
def read_loader():
    for p in [
        Path("satpambot/bot/modules/discord_bot/cogs/cogs_loader.py"),
        Path("satpambot/bot/modules/discord_bot/cogs_loader.py"),
    ]:
        if p.exists():
            s=p.read_text("utf-8"); 
            m=re.search(r"EXTENSIONS\s*=\s*\(\s*(.*?)\)",s,flags=re.DOTALL)
            if not m: continue
            ex=re.findall(r'"([^"]+)"',m.group(1))
            return p.as_posix(), ex
    return None, []
p, ex = read_loader()
print("loader:", p)
print("count:", len(ex))
print("has legacy modules.* :", any(e.startswith('modules.discord_bot.cogs.') for e in ex))
print("first:", ex[:30])
