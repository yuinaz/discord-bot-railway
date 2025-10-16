
# a00_llm_provider_bootstrap.py (v7.4)
import os, logging
from discord.ext import commands
from pathlib import Path
try: import yaml
except Exception: yaml=None
from satpambot.bot.llm_providers import ask as llm_ask
log = logging.getLogger(__name__)
def _apply_yaml_env(d):
    mapping = {"provider":"LLM_PROVIDER","groq_model":"LLM_GROQ_MODEL","gemini_model":"LLM_GEMINI_MODEL","cli_model":"LLM_CLI_MODEL"}
    for k,v in (d or {}).items():
        if k in mapping and v is not None:
            os.environ.setdefault(mapping[k], str(v))
class LLMProviderBootstrap(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self):
        if yaml:
            p = Path("src/terminal-llm-tricks/ai.yaml")
            if p.exists():
                try:
                    data = yaml.safe_load(p.read_text())
                    if isinstance(data, dict): _apply_yaml_env(data); log.info("[llm-bootstrap] loaded ai.yaml")
                except Exception as e:
                    log.info("[llm-bootstrap] ai.yaml load failed: %r", e)
        setattr(self.bot,"llm_ask", llm_ask); log.info("[llm-bootstrap] bot.llm_ask ready")
async def setup(bot):
    try: await bot.add_cog(LLMProviderBootstrap(bot))
    except Exception as e: log.info("[llm-bootstrap] setup swallowed: %r", e)
