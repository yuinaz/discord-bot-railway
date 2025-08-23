
import logging
class _HealthMute(logging.Filter):
    def filter(self, record):
        m = record.getMessage()
        return not ("/healthz" in m or "/uptime" in m)
def install():
    logging.getLogger("werkzeug").addFilter(_HealthMute())
try:
    install()
except Exception:
    pass
