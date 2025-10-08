# scripts/smoke_public_chat_gate.py
"""
Lightweight smoke test to ensure imports and critical symbols exist.
Run:  python -m scripts.smoke_public_chat_gate
"""
from importlib import import_module

def main():
    try:
        m = import_module("satpambot.bot.modules.discord_bot.cogs.public_chat_gate")
        assert hasattr(m, "PublicChatGate"), "Missing PublicChatGate"
        print("[OK] import PublicChatGate")
        m2 = import_module("satpambot.shared.progress_gate")
        assert hasattr(m2, "ProgressGate"), "Missing ProgressGate"
        print("[OK] import ProgressGate")
        print("Smoke OK")
    except Exception as e:
        print("Smoke FAIL:", e)
        raise SystemExit(1)

if __name__ == "__main__":
    main()
