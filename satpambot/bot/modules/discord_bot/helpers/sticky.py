import os, json
from pathlib import Path
def _state_path():
    here = Path(__file__).resolve()
    data_dir = here.parents[3] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "sticky_state.json"
def _load():
    p=_state_path()
    if p.exists():
        try: return json.loads(p.read_text())
        except Exception: return {}
    return {}
def _save(s): _state_path().write_text(json.dumps(s, indent=2))
async def upsert_sticky_embed(channel, embed, key='presence'):
    s=_load(); m=s.setdefault(str(channel.id),{}).get(key)
    try:
        if m:
            msg=await channel.fetch_message(int(m))
            if msg: await msg.edit(embed=embed, content=None)
            return msg
    except Exception: pass
    msg=await channel.send(embed=embed)
    s[str(channel.id)][key]=str(msg.id); _save(s); return msg
