# scripts/smoke_levels.py
from importlib import import_module

def main():
    m1 = import_module("satpambot.shared.progress_gate")
    assert hasattr(m1, "ProgressGate")
    m2 = import_module("satpambot.bot.modules.discord_bot.cogs.self_learning_autoprogress")
    assert hasattr(m2, "SelfLearningAutoProgress")
    m3 = import_module("satpambot.bot.modules.discord_bot.cogs.public_chat_gate")
    assert hasattr(m3, "PublicChatGate")
    print("Smoke OK: multi-level TK(2)+SD(6) loaded")

if __name__ == "__main__":
    main()
