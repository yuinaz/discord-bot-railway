from flask import request, redirect, session, render_template_string
from modules.utils import app
import datetime

@app.route("/editor", methods=["GET", "POST"])
def editor():
    if not session.get("admin"): return redirect("/login")
    filepath = "main.py"
    if request.method == "POST":
        new_code = request.form.get("code")
        confirm = request.form.get("confirm")
        if not confirm:
            return "Perlu konfirmasi sebelum menyimpan", 400
        with open(filepath, "w") as f: f.write(new_code)
        with open("editor_log.txt", "a") as log:
            log.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] main.py diedit dari dashboard\n")
        return redirect("/dashboard")
    try:
        with open(filepath, "r") as f: current_code = f.read()
    except: current_code = ""
    return render_template_string("""<form method='POST'>
    <textarea name='code' rows='25' style='width:100%'>{{ current_code }}</textarea>
    <input type='checkbox' name='confirm' required> Konfirmasi
    <button>Simpan</button></form>""", current_code=current_code)