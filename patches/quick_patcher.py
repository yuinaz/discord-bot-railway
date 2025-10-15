# -*- coding: utf-8 -*-
"""
Quick patcher — extends smoke DummyBot for offline smoke_deep runs.

What it does:
- Finds candidate `smoke_utils.py` files in:
  * satpambot/bot/modules/discord_bot/helpers/smoke_utils.py
  * scripts/smoke_utils.py
  * smoke_utils.py (repo root, if any)
- Appends idempotent monkeypatch stubs for methods commonly awaited/called by cogs:
  wait_until_ready, get_all_channels, get_channel, get_user, fetch_user
- Adds `_DummyBot = DummyBot` alias when missing (some harnesses use this name).
- Makes a timestamped .bak copy before writing.

Safe to run multiple times.
"""
from __future__ import annotations

import io, os, sys, time
from pathlib import Path

PATCH_BANNER = "# === [PATCH: smoke DummyBot runtime stubs] ==="

PATCH_SNIPPET = f"""{PATCH_BANNER}
try:
    DummyBot
except NameError:
    pass
else:
    # Provide awaited/used methods so cogs don't crash under smoke harness.
    if not hasattr(DummyBot, "wait_until_ready"):
        async def _wait_until_ready(self):
            return None
        DummyBot.wait_until_ready = _wait_until_ready  # type: ignore[attr-defined]

    if not hasattr(DummyBot, "get_all_channels"):
        def _get_all_channels(self):
            return []
        DummyBot.get_all_channels = _get_all_channels  # type: ignore[attr-defined]

    if not hasattr(DummyBot, "get_channel"):
        def _get_channel(self, channel_id):
            return None
        DummyBot.get_channel = _get_channel  # type: ignore[attr-defined]

    if not hasattr(DummyBot, "get_user"):
        def _get_user(self, user_id):
            return None
        DummyBot.get_user = _get_user  # type: ignore[attr-defined]

    if not hasattr(DummyBot, "fetch_user"):
        async def _fetch_user(self, user_id):
            return None
        DummyBot.fetch_user = _fetch_user  # type: ignore[attr-defined]

# Some harnesses refer to _DummyBot; keep alias available.
try:
    _DummyBot
except NameError:
    _DummyBot = DummyBot  # type: ignore[name-defined]
"""

def patch_file(path: Path) -> str:
    if not path.exists():
        return f"[skip] not found: {path}"
    src = path.read_text(encoding="utf-8", errors="ignore")
    if PATCH_BANNER in src:
        return f"[info] already patched: {path}"
    # backup
    bak = path.with_suffix(path.suffix + f".bak-{int(time.time())}")
    bak.write_text(src, encoding="utf-8")
    # append patch (ensure newline)
    new_src = src.rstrip() + "\n\n" + PATCH_SNIPPET
    path.write_text(new_src, encoding="utf-8")
    return f"[ok] patched: {path}\n[bak] backup : {bak}"

def main() -> None:
    repo = Path.cwd()
    candidates = [
        repo / "satpambot" / "bot" / "modules" / "discord_bot" / "helpers" / "smoke_utils.py",
        repo / "scripts" / "smoke_utils.py",
        repo / "smoke_utils.py",
    ]
    results = []
    for p in candidates:
        results.append(patch_file(p))
    print("\n".join(results))

if __name__ == "__main__":
    main()
