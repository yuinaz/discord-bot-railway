
from __future__ import annotations
import os
HARDCODE = {
    "TZ": "Asia/Jakarta",
    "QNA_CHANNEL_ID": "1426571542627614772",
    "QNA_CHANNEL_ALLOWLIST": "1426571542627614772",
    "QNA_PROVIDER_ORDER": "groq,gemini",
    "QNA_TOPICS_FILE": "/opt/render/project/src/data/config/qna_topics.json",
    "QNA_PUBLIC_ENABLE": "1",
    "QNA_ANSWER_TTL_SEC": "86400",
    "QNA_XP_AWARD": "5",
    "QNA_ASK_DEDUP_TTL_SEC": "259200",
    "QNA_ASK_RECENT_MAX": "200",
    "LEARNING_MIN_LABEL": "KULIAH-S2",
    "XP_SENIOR_KEY": "xp:bot:senior_total_v2",
    "LADDER_FILE": "/opt/render/project/src/data/neuro-lite/ladder.json",
    "LEARNING_PHASE_DEFAULT": "senior",
}
def env(name: str, default: str|None=None) -> str:
    if default is None:
        default = HARDCODE.get(name, "")
    return os.getenv(name, default)
def env_bool(name: str, default: bool=False) -> bool:
    v = env(name, "1" if default else "0").strip().lower()
    return v in ("1","true","yes","on")
def env_int(name: str, default: int=0) -> int:
    try:
        return int(env(name, str(default)).strip().rstrip(","))
    except Exception:
        return default
