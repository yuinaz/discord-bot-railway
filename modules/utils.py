import os
from flask import Flask
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecret")
app.permanent_session_lifetime = timedelta(days=7)
START_TIME = os.times()
