# Auto-loaded if present on sys.path (repo root). Keeps env 'attached' to the bot.
import os
def _set_default(k, v):
    if os.environ.get(k) in (None, ''):
        os.environ[k] = str(v)
try:
    from dotenv import load_dotenv, find_dotenv
    for cand in ('.env', '.env.local', 'config.env'):
        if os.path.exists(cand):
            load_dotenv(dotenv_path=cand, override=False)
    load_dotenv(find_dotenv(), override=False)
except Exception:
    pass
_set_default('STICKER_ENABLE','0')
_set_default('DISABLED_COGS','name_wake_autoreply')
_set_default('BOOT_DM_ONLINE','0')
_set_default('OPENAI_TIMEOUT_S','20')
_set_default('SELF_LEARNING_ENABLE','1')
_set_default('SELF_LEARNING_SAFETY','conservative')
_set_default('PORT','10000')
_set_default('UPDATE_DM_OWNER','1')
_set_default('MAINTENANCE_AUTO','1')
_set_default('MAINT_HALF_CPU','85')
_set_default('MAINT_RESUME_CPU','50')
_set_default('COMMANDS_OWNER_ONLY','1')
