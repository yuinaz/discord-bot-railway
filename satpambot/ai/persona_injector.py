import json, os
from pathlib import Path

def _load_persona():
    path = os.getenv("PERSONA_PROFILE_PATH","data/config/persona/teen_tsundere.json")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None

def build_system(base: str = "") -> str:
    p = _load_persona() or {}
    name = p.get("name","Leina")
    style = p.get("style",{})
    tone = style.get("tone","ramah, tegas, teknis")
    length = style.get("length","ringkas")
    emoji = style.get("emoji","hemat")
    bounds = p.get("boundaries",{})
    goals = p.get("goals",[])
    addon = p.get("system_addendum","")

    parts = [base or ""]
    parts.append(f"[Persona::{name}] Tone={tone}; Panjang={length}; Emoji={emoji}.")
    if goals:
        parts.append("Tujuan: " + "; ".join(goals))
    if bounds.get("respect_gates"):
        parts.append("Ikuti gate/policy Governor jika aktif.")
    if bounds.get("no_nsfw"):
        parts.append("Jangan membuat konten NSFW.")
    if bounds.get("no_harassment"):
        parts.append("Hindari nada yang menyerang atau melecehkan.")
    if addon:
        parts.append(addon)
    return "\n".join([s for s in parts if s]).strip()
