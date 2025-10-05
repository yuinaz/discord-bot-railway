# Lightweight hooks (no config change). Does NOT start its own Flask server.







import logging

# Quieten health/ping access logs







class _HealthFilter(logging.Filter):







    def filter(self, record):







        try:







            msg = record.getMessage()







        except Exception:







            msg = str(record.msg)







        return ("/healthz" not in msg) and ("/ping" not in msg)























try:







    logging.getLogger("werkzeug").addFilter(_HealthFilter())







    logging.getLogger("gunicorn.access").addFilter(_HealthFilter())







except Exception:







    pass























# Print the same banner once the real app responds to HEAD /







def _banner_probe():







    import http.client
    import os
    import time















    host = "127.0.0.1"







    port = int(os.environ.get("PORT", "10000"))







    deadline = time.time() + 30.0







    while time.time() < deadline:







        try:







            conn = http.client.HTTPConnection(host, port, timeout=1.0)







            conn.request("HEAD", "/")







            resp = conn.getresponse()







            if resp and resp.status in (200, 301, 302, 307, 308):







                print("==> Your service is live 🎉", flush=True)







                return







        except Exception:







            pass







        time.sleep(0.4)







    # If not reachable, stay silent; do not crash the app.























try:







    import threading















    threading.Thread(target=_banner_probe, name="ready-banner", daemon=True).start()







except Exception:







    pass







