# =============================================
# File: pages.py
# Version: 1.0.0-Beta
# Author: Omar Rashad
# Python Version: 3.13.1 (tags/v3.13.1:0671451, Dec  3 2024, 19:06:28) [MSC v.1942 64 bit (AMD64)]
# Last Update: 2025-05-22
# =============================================
import os
from flask import Blueprint, render_template, redirect, abort, jsonify, request, flash
from werkzeug.security import check_password_hash
import psutil
import time
from .printing import print_file
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

bp = Blueprint("pages", __name__)

@bp.route("/")
def home():
    return render_template("pages/home.html")

@bp.route("/about")
def about():
    return render_template("pages/about.html") 

@bp.route('/print', methods=['GET', 'POST'])
def print_page():
    
    HASHED_PRINTER_PASSWORD = os.getenv("PRINTER_API_KEY") # hashed password hint: ors@

    if request.method == 'POST':
        # ---  checks ---
        if not HASHED_PRINTER_PASSWORD:
            flash("Server is not configured for printing. Missing IP or Password environment variable.", "danger")
            return redirect(request.url)

        user_password = request.form.get("password").srtip()
        is_ok_password = check_password_hash(HASHED_PRINTER_PASSWORD, user_password)
        if not user_password or not is_ok_password:
           flash("Invalid password.", "danger")
           return redirect(request.url)
        
        # --- printing Logic ---
        text_to_print = request.form.get('text_to_print')
        file = request.files.get('file_to_print')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            temp_file_path = os.path.join("/tmp", filename)
            file.save(temp_file_path)
            success, message = print_file(temp_file_path)
            os.remove(temp_file_path)
        elif text_to_print:
            temp_file_path = "/tmp/print_job.txt"
            with open(temp_file_path, "w") as f:
                f.write(text_to_print + "\n\f")
            success, message = print_file(temp_file_path)
            os.remove(temp_file_path)
        else:
            flash("No text or file provided to print.", "warning")
            return redirect(request.url)

        if success:
            flash(f"Print job sent successfully! Message: {message}", "success")
        else:
            flash(f"Failed to send print job. Error: {message}", "danger")
        
        return redirect(request.url)

    return render_template('pages/print.html' , password_check= f"is ok password: {is_ok_password}" )
    
@bp.route("/pokeWizy")
def pokeWizy():
    wizy_proc_name = 'bot_wizy_discord.py'
    for proc in psutil.process_iter(['name']):
        try:
            # Compare process name
            if proc.info['name'] == wizy_proc_name:
                return "<a href='https://github.com/orsnaro/Discord-Bot-Ai/tree/production-Home-Server'> <h1 style='color:orange'> Wizy Running🧙‍♂️🟢! </h1> </a>"
        except psutil.NoSuchProcess:
            pass
    time.sleep(4)        
    abort(404, "Wizy not found running in server🔴🥹! I guess he Is sleeping ... what a lazy old man🧙‍♂️!")

@bp.route("/wizyVersion")
def wizyVersion():
    version = "🧙‍♂️?!"
    with open("/home/ors/repos/Discord_bot_ai/version.txt", "r") as versionFile:
        version = versionFile.read()
    paylaod = { "schemaVersion": 1, "label": "Hosted Version", "message": version, "color": "#1D63ED" }
    return jsonify(paylaod)

@bp.route("/wizy-status")
def wizy_status():
    wizy_proc_name = 'bot_wizy_discord.py'
    is_running = False
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] == wizy_proc_name:
                is_running = True
                break
        except psutil.NoSuchProcess:
            pass
    return render_template("pages/wizy_status.html", is_running=is_running)

@bp.route("/api-info")
def api_info():
    version = "🧙‍♂️"
    try:
        with open("board/version.txt", "r") as versionFile:
            version = versionFile.read().strip()
    except Exception:
        version = "Unknown"
    return render_template("pages/api_info.html", version=version)

@bp.route("/server")
def server_status():
    stats = {
        'cpu_percent': psutil.cpu_percent(interval=0.5),
        'memory': psutil.virtual_memory(),
        'uptime': int(time.time() - psutil.boot_time()),
        'users': psutil.users(),
        'loadavg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
    }
    return render_template("pages/server_status.html", stats=stats)
