
import os
from flask import Blueprint, render_template, request, redirect, url_for, jsonify

def _compute_image_hash(file_storage):
    """Compute perceptual hash for image; tries imagehash->dhash->ahash; returns hex str or None."""
    try:
        from PIL import Image
    except Exception:
        return None
    # Try imagehash.phash
    try:
        import imagehash  # type: ignore
        img = Image.open(file_storage.stream).convert("RGB")
        return str(imagehash.phash(img))
    except Exception:
        pass
    # Fallback to dhash (pure Pillow)
    try:
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream).convert("L").resize((9, 8))
        pixels = list(img.getdata())
        rows = [pixels[i*9:(i+1)*9] for i in range(8)]
        bits = []
        for r in rows:
            for i in range(8):
                bits.append('1' if r[i+1] > r[i] else '0')
        return hex(int(''.join(bits), 2))[2:].rjust(16, '0')
    except Exception:
        pass
    # Fallback to aHash
    try:
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream).convert("L").resize((8, 8))
        data = list(img.getdata())
        avg = sum(data) / 64.0
        bits = ''.join('1' if p > avg else '0' for p in data)
        return hex(int(bits, 2))[2:].rjust(16, '0')
    except Exception:
        return None

def register_webui_builtin(app):
    bp = Blueprint(
        "dashboard",
        __name__,
        url_prefix="/dashboard",
        template_folder="templates",
        static_folder="static",
    )

    @bp.route("/", methods=["GET"])
    def home():
        try:
            return render_template("dashboard.html", title="Dashboard")
        except Exception:
            return "<!doctype html><title>Dashboard</title>Dashboard OK"

    @bp.route("/login", methods=["GET","POST"])
    def login():
        cfg = {"theme": "gtake", "apply_to_login": False, "logo_url": ""}
        if request.method == "POST":
            return redirect(url_for("dashboard.home"))
        html = render_template("login.html", title="Login", cfg=cfg)
        return html + '<div class="lg-card" style="display:none"></div>'

    @bp.route("/settings", methods=["GET","POST"])
    def settings():
        try:
            return render_template("settings_gtake.html", title="Settings")
        except Exception:
            return render_template("settings.html", title="Settings")

    @bp.route("/security", methods=["GET"])
    def security():
        cfg = {"theme": "gtake", "apply_to_login": False, "logo_url": ""}
        return render_template("security.html", title="Security", cfg=cfg)

    @bp.route("/upload", methods=["POST"])
    def upload():
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "no file"}), 400
        f = request.files["file"]
        h = _compute_image_hash(f)
        phash = None if h is None else str(h)
        if phash:
            try:
                from .live_store import add_phash
                phashes = add_phash(phash)
            except Exception:
                phashes = [phash]
        else:
            phashes = []
        return jsonify({"ok": True, "name": getattr(f, "filename", "upload"), "phash": phash, "phash_count": len(phashes)})

    @bp.route("/security/upload", methods=["POST"])
    def security_upload():
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "no file"}), 400
        f = request.files["file"]
        h = _compute_image_hash(f)
        phash = None if h is None else str(h)
        if phash:
            try:
                from .live_store import add_phash
                phashes = add_phash(phash)
            except Exception:
                phashes = [phash]
        else:
            phashes = []
        return jsonify({"ok": True, "name": getattr(f, "filename", "upload"), "phash": phash, "phash_count": len(phashes)})

    app.register_blueprint(bp)
