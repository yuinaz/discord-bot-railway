
# scripts/smoketest_dashboard_routes.py
import json, sys
from app import app

def main():
    ok = True
    with app.test_client() as c:
        # dashboard main
        r = c.get("/dashboard/")
        print("GET /dashboard =>", r.status_code)
        ok = ok and (r.status_code == 200)

        # metrics must be present
        r = c.get("/dashboard/api/metrics")
        print("GET /dashboard/api/metrics =>", r.status_code, r.json)
        ok = ok and (r.status_code == 200 and isinstance(r.json, dict))

        # banned users endpoint
        r = c.get("/dashboard/api/banned_users")
        print("GET /dashboard/api/banned_users =>", r.status_code, list(r.json or {}))
        ok = ok and (r.status_code == 200)

        # phash upload should reject GET but exist
        r = c.get("/dashboard/api/phash/upload")
        print("GET /dashboard/api/phash/upload =>", r.status_code)
        ok = ok and (r.status_code in (400,405))

    print("OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
