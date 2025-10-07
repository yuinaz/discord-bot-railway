# -*- coding: utf-8 -*-
import os, sys

def main():
    ok = True
    key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI-KEY")
    if not key:
        print("WARN : OPENAI key not found (OPENAI_API_KEY / OPENAI-KEY). Self-heal/chat may be limited.")
    else:
        print("OK   : OPENAI key present.")

    files = [
        "satpambot/bot/modules/discord_bot/helpers/openai_client.py",
        "satpambot/bot/modules/discord_bot/cogs/chat_neurolite.py",
        "satpambot/bot/modules/discord_bot/cogs/self_heal_runtime.py",
    ]
    for f in files:
        if not os.path.exists(os.path.join("/mnt/data/patch_openai_v1", f)) and not os.path.exists(f):
            print(f"FAIL : missing {f}")
            ok = False
        else:
            print(f"OK   : {f} (exists)")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
