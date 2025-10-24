"""
auto_defaults v2
Priority: ENV -> JSON override(s) -> builtin defaults.
JSON override search order:
  1) ENV["CONFIG_OVERRIDES_PATH"] if exists
  2) data/config/overrides.render-free.json
  3) data/config/auto_defaults.json

Alias keys supported:
  QNA_TOPICS_PATH   <- QNA_TOPICS_FILE
  QNA_PROVIDER      <- QNA_PROVIDER_ORDER  (comma list => first)
  QNA_PUBLIC_GATE   <- QNA_PUBLIC_ENABLE   ('1'/'true' => 'unlock', else 'lock')
  QNA_PUBLIC_CHANNEL_ID <- PUBLIC_QNA_CHANNEL_ID, PUBLIC_CHANNEL_ID
  GROQ_MODEL        <- LLM_GROQ_MODEL
  GEMINI_MODEL      <- LLM_GEMINI_MODEL
"""

from __future__ import annotations
import os, json
from pathlib import Path
from typing import Any, Dict, List

BUILTIN_DEFAULTS: Dict[str, Any] = {
    "QNA_CHANNEL_ID": "1426571542627614772",
    "QNA_PROVIDER": "groq",
    "QNA_TOPICS_PATH": "data/config/qna_topics.json",
    "AUTOLEARN_PERIOD_SEC": "60",
    "QNA_PUBLIC_CHANNEL_ID": "886534544688308265",
    "QNA_PUBLIC_GATE": "lock",
    "QNA_XP_PER_ANSWER_BOT": "5",
    "XP_SENIOR_KEY": "xp:bot:senior_total_v2",
    "QNA_AWARD_IDEMP_NS": "qna:awarded:answer",
    "QNA_AUTOLEARN_IDEM_NS": "qna:asked",
    "CONFIG_OVERRIDES_PATH": "data/config/overrides.render-free.json",
}

ALIASES: Dict[str, List[str]] = {
    "QNA_TOPICS_PATH": ["QNA_TOPICS_FILE"],
    "QNA_PROVIDER": ["QNA_PROVIDER_ORDER"],
    "QNA_PUBLIC_GATE": ["QNA_PUBLIC_ENABLE"],
    "QNA_PUBLIC_CHANNEL_ID": ["PUBLIC_QNA_CHANNEL_ID", "PUBLIC_CHANNEL_ID"],
    "GROQ_MODEL": ["LLM_GROQ_MODEL"],
    "GEMINI_MODEL": ["LLM_GEMINI_MODEL"],
}

def _normalize_alias_value(key: str, value: str) -> str:
    k = key.upper(); v = (value or "").strip()
    if k == "QNA_PROVIDER":
        parts = [p.strip() for p in v.split(",") if p.strip()]
        return parts[0].lower() if parts else ""
    if k == "QNA_PUBLIC_GATE":
        return "unlock" if v.lower() in ("1","true","yes","on","unlock") else "lock"
    return v

def _load_json_overrides() -> Dict[str, Any]:
    paths = []
    env_override = os.getenv("CONFIG_OVERRIDES_PATH", "").strip()
    if env_override:
        paths.append(Path(env_override))
    paths.append(Path("data/config/overrides.render-free.json"))
    paths.append(Path("data/config/auto_defaults.json"))
    for p in paths:
        try:
            if p.exists():
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if "env" in data and isinstance(data["env"], dict):
                            data = data["env"]
                        return {str(k): str(v) for k, v in data.items()}
        except Exception:
            continue
    return {}

_JSON = _load_json_overrides()

def _get_with_alias(key: str, source: Dict[str, Any]) -> str:
    if key in source and str(source[key]).strip() != "":
        return str(source[key]).strip()
    for ak in ALIASES.get(key, []):
        if ak in source and str(source[ak]).strip() != "":
            return _normalize_alias_value(key, str(source[ak]))
    return ""

def cfg_str(key: str, default: str = "") -> str:
    k = key.upper()
    v = os.getenv(k, "").strip()
    if not v and k in ALIASES:
        for ak in ALIASES[k]:
            vv = os.getenv(ak, "").strip()
            if vv:
                v = _normalize_alias_value(k, vv); break
    if v:
        return v
    v = _get_with_alias(k, _JSON)
    if v:
        return v
    v = _get_with_alias(k, BUILTIN_DEFAULTS)
    if v:
        return v
    return default

def cfg_int(key: str, default: int | None = None) -> int | None:
    s = cfg_str(key, "")
    if s == "":
        return default
    try:
        return int(s)
    except Exception:
        return default
