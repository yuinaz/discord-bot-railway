import os, json, time
from flask import Blueprint, request, jsonify, render_template
from PIL import Image
import imagehash

DATA_DIR = os.environ.get("SATPAMBOT_DATA_DIR", "data")
PHASH_JSON = os.path.join(DATA_DIR, "phish_phash.json")
HASH_TXT = os.environ.get("SATPAMBOT_PHASH_TXT", "blacklist_image_hashes.txt")

phish_api = Blueprint("phish_api", __name__)

def _ensure_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PHASH_JSON):
        with open(PHASH_JSON, "w", encoding="utf-8") as f:
            json.dump({"hashes": []}, f, ensure_ascii=False)
    if not os.path.exists(HASH_TXT):
        open(HASH_TXT, "a", encoding="utf-8").close()

def _load():
    _ensure_files()
    with open(PHASH_JSON, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {"hashes": []}
    return data

def _save(data):
    with open(PHASH_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@phish_api.route("/dashboard/api/phash/list", methods=["GET"])
def phash_list():
    data = _load()
    return jsonify({"total": len(data.get("hashes", [])), "hashes": data.get("hashes", [])})

@phish_api.route("/dashboard/api/phash/upload", methods=["POST"])
def phash_upload():
    _ensure_files()
    files = []
    if request.files:
        for k in request.files:
            fs = request.files.getlist(k)
            files.extend(fs)
    if not files:
        return jsonify({"error": "no files"}), 400

    data = _load()
    known = set([h["hash"] if isinstance(h, dict) else h for h in data.get("hashes", [])])
    added, skipped = [], []

    for f in files:
        try:
            img = Image.open(f.stream).convert("RGB")
            ph = str(imagehash.phash(img))
            if ph in known:
                skipped.append(ph)
                continue
            item = {"hash": ph, "filename": f.filename, "ts": int(time.time())}
            data.setdefault("hashes", []).append(item)
            known.add(ph)
            added.append(item)
        except Exception:
            skipped.append(f"{f.filename or 'file'}:error")
            continue

    _save(data)

    try:
        with open(HASH_TXT, "w", encoding="utf-8") as out:
            for it in data["hashes"]:
                out.write((it["hash"] if isinstance(it, dict) else str(it)) + "\n")
    except Exception:
        pass

    return jsonify({"added": added, "skipped": skipped, "total": len(data.get("hashes", []))})

# Simple stubs to avoid 404 while you wire real pages
@phish_api.route("/dashboard/tasks", methods=["GET"])
def dashboard_tasks():
    return render_template("stubs/tasks.html")

@phish_api.route("/dashboard/options", methods=["GET"])
def dashboard_options():
    return render_template("stubs/options.html")

def register_phish_routes(app):
    app.register_blueprint(phish_api)
