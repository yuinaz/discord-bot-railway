# scripts/smoke_autoprogress.py
from importlib import import_module
def main():
    m = import_module("satpambot.bot.modules.discord_bot.cogs.self_learning_autoprogress")
    assert hasattr(m, "SelfLearningAutoProgress"), "Missing SelfLearningAutoProgress"
    m2 = import_module("satpambot.bot.modules.discord_bot.cogs.public_chat_gate")
    assert hasattr(m2, "PublicChatGate"), "Missing PublicChatGate"
    print("Smoke OK: autoprogress + gate present")
if __name__ == "__main__":
    main()
