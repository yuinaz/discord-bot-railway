"""
Smoke test: ensure handle_on_message does NOT swallow '!' commands
and that it forwards exactly once to message.bot.process_commands.
Auto-detects project root. Run with:
  python scripts/smoke_test_message_flow.py
"""
import asyncio
import sys
from pathlib import Path

# Auto-add project root
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from modules.discord_bot.message_handlers import handle_on_message  # type: ignore
except Exception as e:
    print("❌ Import failed:", e)
    print("Hint: ensure this file is inside <project>/scripts/ and run: python scripts/smoke_test_message_flow.py")
    raise

class DummyBot:
    def __init__(self):
        self.calls = 0
    async def process_commands(self, message):
        self.calls += 1

class DummyAuthor:
    def __init__(self):
        self.bot = False

class DummyMessage:
    def __init__(self, content, bot):
        self.content = content
        self.author = DummyAuthor()
        self._bot = bot
    @property
    def bot(self):
        return self._bot
    @bot.setter
    def bot(self, value):
        self._bot = value
    @property
    def guild(self):
        return None

async def run_case(text):
    b = DummyBot()
    m = DummyMessage(text, b)
    await handle_on_message(m, b)
    return b.calls

async def main():
    # Case 1: '!' command should NOT call process_commands inside handle_on_message
    calls = await run_case("!testban @user")
    print("Case 1: calls to process_commands =", calls)
    assert calls == 0, "handle_on_message should early-return for '!' content"

    # Case 2: normal message should forward once
    calls = await run_case("hello world")
    print("Case 2: calls to process_commands =", calls)
    assert calls == 1, "normal message should forward exactly once"

    print("✅ Message flow tests passed.")

if __name__ == "__main__":
    asyncio.run(main())
