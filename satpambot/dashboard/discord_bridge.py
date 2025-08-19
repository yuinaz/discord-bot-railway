from __future__ import annotations
import typing as t, time
from dataclasses import dataclass, asdict
bot_ref = {"bot": None}

def set_bot(bot): bot_ref["bot"]=bot

def _guild():
    b = bot_ref.get("bot")
    if not b: return None
    g = None
    try:
        # Prefer first guild if single-tenant
        g = b.guilds[0] if getattr(b,'guilds',None) else None
    except Exception:
        g=None
    return g

def snapshot()->dict:
    g = _guild()
    if not g: return {"member_count":0,"online_count":0,"channels_total":0,"threads_total":0}
    # member and online counts
    mc = getattr(g, "member_count", 0) or 0
    oc = 0
    try:
        for m in g.members:
            try:
                if m.status and str(m.status) != 'offline':
                    oc += 1
            except Exception:
                pass
    except Exception:
        oc = 0
    # channels & threads
    ch_total = len(getattr(g, "channels", []) or [])
    th_total = 0
    try:
        for ch in g.channels:
            try:
                th_total += len(getattr(ch, "threads", []) or [])
            except Exception:
                pass
    except Exception:
        pass
    return {"member_count": mc, "online_count": oc, "channels_total": ch_total, "threads_total": th_total}
