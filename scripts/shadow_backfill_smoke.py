#!/usr/bin/env python3
import os
from satpambot.bot.modules.discord_bot.helpers.phase_utils import get_phase, get_tk_total, get_senior_total

def main():
    upstash = bool(os.getenv("KV_BACKEND") == "upstash_rest" and os.getenv("UPSTASH_REDIS_REST_URL") and os.getenv("UPSTASH_REDIS_REST_TOKEN"))
    print("[shadow-smoke] upstash_enabled =", upstash)
    print("[shadow-smoke] phase =", get_phase())
    print("[shadow-smoke] tk_total =", get_tk_total())
    print("[shadow-smoke] senior_total =", get_senior_total())

if __name__ == "__main__":
    main()