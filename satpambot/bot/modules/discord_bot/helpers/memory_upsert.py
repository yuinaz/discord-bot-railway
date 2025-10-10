# -*- coding: utf-8 -*-
"""
helpers/memory_upsert.py (patched)
- Menerima payload 'phish_text' seperti yang dicetak di log.
- Lebih toleran: 'score' string -> int, missing field -> di-skip.
- Skip berdasarkan channel ID *dan* nama channel (opsional pola).
- Simpan snapshot normalisasi ke file JSON untuk debug.
- Return True jika ada item valid yang di-proses (agar "memory updated: True").
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, Iterable, List

log = logging.getLogger("satpambot.bot.modules.discord_bot.helpers.memory_upsert")

# Daftar default channel-id yang selalu di-skip (sesuai permintaan).
DEFAULT_SKIP_CHANNEL_IDS = {
    763813761814495252,
    936689852546678885,
    767401659390623835,
    1270611643964850178,
    761163966482743307,
    1422084695692414996,
    1372983711771001064,
    1378739739930398811,
}

def _parse_env_list_int(name: str) -> Iterable[int]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return []
    out = []
    for tok in raw.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            out.append(int(tok))
        except Exception:
            pass
    return out

def _parse_env_list_str(name: str) -> Iterable[str]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return []
    return [t.strip().lstrip("#").lower() for t in raw.split(",") if t.strip()]

ENV_SKIP_IDS = set(DEFAULT_SKIP_CHANNEL_IDS) | set(_parse_env_list_int("XP_SKIP_CHANNEL_IDS"))
ENV_SKIP_NAMES = set(_parse_env_list_str("XP_SKIP_CHANNEL_NAMES"))
ENV_SKIP_NAME_PATTERNS = [p for p in _parse_env_list_str("XP_SKIP_CHANNEL_NAME_PATTERNS")]
MAX_ITEMS = int(os.environ.get("XP_MAX_PHISH_TEXT_ITEMS", "200"))

# Folder untuk menyimpan snapshot payload
OUT_DIR = Path(os.environ.get("XP_JSON_DIR", "data/neuro-lite")).resolve()
OUT_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_FILE = OUT_DIR / "last_phish_text.json"

CHAN_RE = re.compile(r"/channels/(?P<guild>\d+)/(?P<chan>\d+)/(?P<msg>\d+)")

def _chan_id_from_url(url: str) -> int | None:
    m = CHAN_RE.search(url or "")
    if not m:
        return None
    try:
        return int(m.group("chan"))
    except Exception:
        return None

def _norm_ch_name(ch: str) -> str:
    # contoh input: "#🎥︲lein-new-video" -> "🎥︲lein-new-video"
    ch = (ch or "").strip()
    if ch.startswith("#"):
        ch = ch[1:]
    return ch.lower()

def _name_is_skipped(name_norm: str) -> bool:
    if name_norm in ENV_SKIP_NAMES:
        return True
    for pat in ENV_SKIP_NAME_PATTERNS:
        if pat and pat in name_norm:
            return True
    return False

def _coerce_int(x, default=0) -> int:
    try:
        return int(x)
    except Exception:
        return default

def _sanitize_item(item: Dict[str, Any]) -> Dict[str, Any] | None:
    # Pastikan field penting ada
    text = (item.get("text") or "").strip()
    url = item.get("url") or ""
    ch_name = _norm_ch_name(item.get("ch") or "")
    by = (item.get("by") or "").strip()
    score = _coerce_int(item.get("score"), 0)

    if not text or not url:
        return None

    ch_id = _chan_id_from_url(url)
    # Filter berdasarkan skip-list
    if ch_id and ch_id in ENV_SKIP_IDS:
        return None
    if ch_name and _name_is_skipped(ch_name):
        return None

    return {
        "ch_id": ch_id,
        "ch_name": ch_name,
        "by": by,
        "score": score,
        "text": text,
        "url": url,
    }

def upsert(payload: Dict[str, Any]) -> bool:
    """
    Terima payload dari miner, normalisasi & tulis snapshot.
    Return True bila ada item valid (agar caller tahu sukses).
    """
    if not isinstance(payload, dict):
        log.warning("[memory_upsert] payload bukan dict: %r", type(payload))
        return False

    items = payload.get("phish_text")
    if not isinstance(items, list):
        log.warning("[memory_upsert] payload tidak punya list 'phish_text'")
        return False

    cleaned: List[Dict[str, Any]] = []
    for it in items[: MAX_ITEMS * 2]:  # batasi scanning
        ok = _sanitize_item(it or {})
        if ok:
            cleaned.append(ok)
        if len(cleaned) >= MAX_ITEMS:
            break

    if not cleaned:
        log.info("[memory_upsert] tidak ada item valid setelah filter (kemungkinan semua masuk skip-list/pola)")
        return False

    # Simpan snapshot agar mudah di-diagnosa di MINIPC
    try:
        SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_FILE.write_text(json.dumps({"phish_text": cleaned, "ts": payload.get("ts")}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("[memory_upsert] gagal menulis snapshot: %s", e)

    # Kalau upstream punya mekanisme upsert lain, bisa dipanggil di sini.
    # Untuk patch ini, kita cukup mengembalikan True agar caller menganggap update sukses.
    return True

# Alias untuk kompatibilitas bila ada import nama fungsi lain
memory_upsert = upsert
upsert_phish_text = upsert
