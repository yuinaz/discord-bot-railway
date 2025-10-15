#!/usr/bin/env python3
"""
Dump raw Upstash GET results for keys to help debugging.
"""
import os, json
from satpambot.bot.modules.discord_bot.helpers.phase_utils import upstash_get, PHASE_KEY, TK_KEY, SENIOR_KEY

def main():
    for key in [PHASE_KEY, TK_KEY, SENIOR_KEY]:
        val, err = upstash_get(key)
        print(f"{key} =>", repr(val), "| err:", err)

if __name__ == "__main__":
    main()