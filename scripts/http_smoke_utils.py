
import json

class HttpSmokeClient:
    def __init__(self, app):
        self.app = app
        self.kind = None
        mod = getattr(app.__class__, "__module__", "").lower()
        if "flask" in mod:
            self.kind = "flask"
            self.client = app.test_client()
        else:
            try:
                from fastapi.testclient import TestClient
                self.kind = "fastapi"
                self.client = TestClient(app)
            except Exception:
                from starlette.testclient import TestClient
                self.kind = "starlette"
                self.client = TestClient(app)

    def get(self, path, **kw):
        return self.client.get(path, **kw)

    def head(self, path, **kw):
        return self.client.head(path, **kw)

    def assert_status(self, resp, expected:list):
        code = getattr(resp, "status_code", None)
        return code in expected, code

    def json(self, resp):
        try:
            if hasattr(resp, "json"):
                return resp.json()
            return json.loads(resp.data.decode("utf-8"))
        except Exception:
            return None
