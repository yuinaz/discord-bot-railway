
# Silence /healthz logs for Werkzeug/Gunicorn
import logging
class _F(logging.Filter):
    def filter(self, record):
        try: msg = record.getMessage()
        except Exception: msg = str(record.msg)
        return ("/healthz" not in msg) and ("/health" not in msg) and ("/ping" not in msg)
logging.getLogger("werkzeug").addFilter(_F())
logging.getLogger("gunicorn.access").addFilter(_F())
