import importlib, os, sys

def ok(tag):
    print(f"[OK] {tag}")

def fail(tag, e):
    print(f"[FAIL] {tag}: {e}")

try:
    import groq  # noqa
    ok("groq installed")
except Exception as e:
    fail("groq not installed", e)

try:
    mod = importlib.import_module("satpambot.ai.llm_client")
    ok("import: satpambot.ai.llm_client")
except Exception as e:
    fail("import: satpambot.ai.llm_client", e)

try:
    mod = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.warn_reaction_blocker")
    ok("import: satpambot.bot.modules.discord_bot.cogs.warn_reaction_blocker")
except Exception as e:
    fail("import: satpambot.bot.modules.discord_bot.cogs.warn_reaction_blocker", e)

print("-- OK if both imports show [OK]")
