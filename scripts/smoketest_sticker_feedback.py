#!/usr/bin/env python3
import importlib, json, os
from pathlib import Path

MOD = "satpambot.bot.modules.discord_bot.cogs.sticker_feedback"

def main():
    importlib.import_module(MOD)
    cfg_path = Path("config/sticker_feedback.json")
    target = int(os.getenv("STICKER_FEEDBACK_TARGET_ID", "0") or 0)
    if cfg_path.exists():
        j = json.loads(cfg_path.read_text(encoding="utf-8"))
        target = int(j.get("target_id", target) or 0)
    if not target:
        lp = Path("config/learning_progress.json")
        if lp.exists():
            j = json.loads(lp.read_text(encoding='utf-8'))
            target = int(j.get("report_channels", {}).get("default") or 0)
    print(f"OK   : import {MOD}")
    print(f"OK   : sticker target_id = {target or '(none)'}; dm=OFF (via config/env)")
    if not target:
        print("WARN : target_id belum di-set; akan fallback ke log channel/env.")
if __name__ == "__main__":
    main()
