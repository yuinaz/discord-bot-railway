import os, json, asyncio
from pathlib import Path

def _state_path():
    # .../satpambot/bot/modules/discord_bot/helpers -> /satpambot/bot/data
    here = Path(__file__).resolve()
    data_dir = here.parents[3] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "sticky_state.json"

def _load():
    p = _state_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}

def _save(state):
    _state_path().write_text(json.dumps(state, indent=2))

async def upsert_sticky(channel, content, key="presence"):
    """Edit satu pesan (sticky) per key di channel itu; kalau belum ada → kirim baru."""
    state = _load()
    chan_map = state.setdefault(str(channel.id), {})
    msg_id = chan_map.get(key)
    try:
        if msg_id:
            msg = await channel.fetch_message(int(msg_id))
            if msg and (msg.content != content):
                await msg.edit(content=content)
            return msg
    except Exception:
        pass
    # buat baru
    msg = await channel.send(content)
    chan_map[key] = str(msg.id)
    _save(state)
    return msg
