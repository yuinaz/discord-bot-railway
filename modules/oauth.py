from flask import request, redirect, session
from modules.utils import app
import os, requests

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")

@app.route("/login")
def login():
    return redirect("https://discord.com/api/oauth2/authorize?" +
        f"client_id={CLIENT_ID}&redirect_uri={OAUTH_REDIRECT_URI}&response_type=code&scope=identify")

@app.route("/callback")
def callback():
    code = request.args.get("code")
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "scope": "identify"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    if r.status_code != 200: return "OAuth failed", 403
    access_token = r.json().get("access_token")
    user = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"}).json()
    if str(user.get("id")) in ADMIN_IDS:
        session["admin"] = True
        session["admin_name"] = user.get("username")
        return redirect("/dashboard")
    return "Akses ditolak", 403

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")