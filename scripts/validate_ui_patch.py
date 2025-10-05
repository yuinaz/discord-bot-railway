from pathlib import Path
import importlib, sys

ROOT = Path(".")
assert (ROOT/"satpambot/dashboard/static/dashboard.css").exists(), "dashboard.css missing"
assert (ROOT/"satpambot/dashboard/static/img/logo.svg").exists(), "logo.svg missing"
assert (ROOT/"satpambot/dashboard/templates/login.html").exists(), "login.html missing"

print("Files OK ✓")

# Coba import Flask app & cek endpoint
sys.path.insert(0, ".")
mod = importlib.import_module("satpambot.dashboard.app")
app = getattr(mod, "app", None)
assert app is not None, "Flask app not found in satpambot.dashboard.app"

with app.test_client() as c:
    r = c.get("/login")
    assert r.status_code in (200,302), f"/login status={r.status_code}"
    r = c.get("/discord/login", follow_redirects=False)
    assert r.status_code in (302,301), f"/discord/login status={r.status_code}"
    r = c.post("/upload/background", data={}, content_type="multipart/form-data")
    assert r.status_code == 400, f"/upload/background expect 400 w/o file, got {r.status_code}"
print("Routes OK ✓")
