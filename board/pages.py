# =============================================
# File: pages.py
# Version: 1.0.3-Beta
# Author: Omar Rashad
# Python Version: 3.13.1 (tags/v3.13.1:0671451, Dec  3 2024, 19:06:28) [MSC v.1942 64 bit (AMD64)]
# Last Update: 2026-05-07
# =============================================
import os
import subprocess
import platform
from flask import Blueprint, render_template, redirect, abort, jsonify, request, flash, url_for
from werkzeug.security import check_password_hash
import psutil
import time
from .printing import print_file, get_printer_status
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

bp = Blueprint("pages", __name__)

# --- Services Registry ---
SERVICES = [
    {
        "id": "printer",
        "name": "Print Anywhere",
        "icon": "🖨️",
        "description": "Send documents or notes to Omar's home printer.",
        "link": "pages.printer",
        "type": "page",
        "custom_check": get_printer_status,
        "is_protected": True
    },
    {
        "id": "wizy",
        "name": "Discord Bot Wizy",
        "icon": "🧙‍♂️",
        "description": "Discord Bot Ai (Wizard GPTeous).",
        "link": "pages.wizy_status",
        "type": "page",
        "proc_name": "bot_wizy_discord.py",
        "is_protected": False
    },
    {
        "id": "server_stats",
        "name": "Server Status",
        "icon": "📊",
        "description": "Real-time CPU, Memory, and Uptime monitoring.",
        "link": "pages.server_status",
        "type": "page",
        "is_protected": False
    },
    {
        "id": "openclaw",
        "name": "OpenClaw Service",
        "icon": "🐾",
        "description": "OpenClaw Agent",
        "type": "info",
        "proc_name": "openclaw",
        "custom_info": True, # Flag to show a 'View Status' button
        "is_protected": True
    },
    {
        "id": "docker",
        "name": "Docker Containers",
        "icon": "🐳",
        "description": "Running docker containers and status.",
        "link": "pages.docker_status",
        "type": "page",
        "is_protected": False
    },
    {
        "id": "ollama",
        "name": "Ollama Models",
        "icon": "🦙",
        "description": "Local LLMs running via Ollama.",
        "link": "pages.ollama_status",
        "type": "page",
        "is_protected": False
    },
    {
        "id": "mongodb",
        "name": "MongoDB Engine",
        "icon": "🍃",
        "description": "Database engine status.",
        "type": "info",
        "proc_name": "mongod",
        "is_protected": False
    }
]

# --- Global state for network speed calculation ---
last_net_io = None
last_net_time = None

def get_docker_containers():
    # If on Windows, we could try to check if docker is running first
    # But usually docker is used in Linux environments for these types of servers
    try:
        # Get container info: ID, Name, Status, Image
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.ID}}|{{.Names}}|{{.Status}}|{{.Image}}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return []
        
        containers = []
        for line in result.stdout.strip().split("\n"):
            if not line: continue
            parts = line.split("|")
            if len(parts) == 4:
                containers.append({
                    "id": parts[0],
                    "name": parts[1],
                    "status": parts[2],
                    "image": parts[3]
                })
        return containers
    except Exception:
        return []

def get_ollama_models():
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return []
        
        models = []
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1: # Skip header
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 1:
                    models.append({
                        "name": parts[0],
                        "id": parts[1] if len(parts) > 1 else "N/A",
                        "size": parts[2] if len(parts) > 2 else "N/A",
                        "modified": " ".join(parts[3:]) if len(parts) > 3 else "N/A"
                    })
        return models
    except Exception:
        return []

def get_power_draw():
    # Attempt to read power draw from /sys/class/power_supply or similar (Linux)
    if platform.system() != "Windows":
        try:
            # Check for battery power (e.g. laptop server)
            for ps in os.listdir("/sys/class/power_supply/"):
                path = f"/sys/class/power_supply/{ps}/power_now"
                if os.path.exists(path):
                    with open(path, "r") as f:
                        # value is usually in microwatts
                        microwatts = int(f.read().strip())
                        return round(microwatts / 1_000_000, 2)
        except Exception:
            pass
        
        # Alternative: check for 'upower' command
        try:
            result = subprocess.run(["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "energy-rate:" in line:
                        rate_str = line.split(":")[1].strip().split(" ")[0]
                        return round(float(rate_str), 2)
        except Exception:
            pass
    else:
        # Windows: try to get battery info which sometimes includes power rate
        try:
            battery = psutil.sensors_battery()
            if battery:
                # psutil doesn't directly give Watts, but we can indicate if it's plugged in
                return "Plugged In" if battery.power_plugged else f"{battery.percent}%"
        except Exception:
            pass

    return "N/A"

def get_network_speeds():
    global last_net_io, last_net_time
    
    current_io = psutil.net_io_counters()
    current_time = time.time()
    
    if last_net_io is None:
        last_net_io = current_io
        last_net_time = current_time
        return 0, 0
    
    time_delta = current_time - last_net_time
    if time_delta <= 0:
        return 0, 0
    
    sent_speed = (current_io.bytes_sent - last_net_io.bytes_sent) / time_delta
    recv_speed = (current_io.bytes_recv - last_net_io.bytes_recv) / time_delta
    
    last_net_io = current_io
    last_net_time = current_time
    
    # Return speeds in bytes/sec
    return round(sent_speed, 2), round(recv_speed, 2)

@bp.route("/services/verify-passcode", methods=["POST"])
def verify_dashboard_passcode():
    entered_passcode = request.json.get("passcode")
    stored_passcode = os.getenv("SERVER_UI_SERVICES_PASSCODE")
    
    if not stored_passcode:
        return jsonify({"success": False, "message": "Server passcode not configured."}), 500
        
    if entered_passcode == stored_passcode:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Invalid passcode."})

def get_service_status(service):
    # Case 1: Custom Python function check
    if "custom_check" in service and callable(service["custom_check"]):
        return service["custom_check"]()

    # Case 2: Process name check
    if "proc_name" in service:
        for proc in psutil.process_iter(['name']):
            try:
                if service["proc_name"] in proc.info['name']:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    
    # Default (e.g. Server Status is always "Live" if the web server is up)
    if service["id"] == "server_stats":
        return True

    return False

@bp.route("/")
def home():
    return render_template("pages/home.html")

@bp.route("/services")
def services():
    services_with_status = []
    for s in SERVICES:
        # Create a copy to avoid mutating the registry
        s_copy = s.copy()
        s_copy["is_running"] = get_service_status(s)
        services_with_status.append(s_copy)
    return render_template("pages/services.html", services=services_with_status)

@bp.route("/services/exec/<service_id>", methods=["POST"])
def service_command(service_id):
    HASHED_PASSWORD = os.getenv("PRINTER_API_KEY")
    user_password = request.form.get("password", "").strip()

    if not HASHED_PASSWORD:
        flash("Server is not configured with an API Key.", "danger")
        return redirect(url_for("pages.services"))

    if not check_password_hash(HASHED_PASSWORD, user_password):
        flash("Invalid access key.", "danger")
        return redirect(url_for("pages.services"))

    # Find the service
    service = next((s for s in SERVICES if s["id"] == service_id), None)
    if not service or service.get("type") != "command":
        flash("Invalid service or command.", "danger")
        return redirect(url_for("pages.services"))

    # Platform Check
    if platform.system() == "Windows":
        flash(f"Command execution is disabled on Windows: {service['command']}", "warning")
        return redirect(url_for("pages.services"))

    # Execute Command
    try:
        # Using shell=True carefully since the command is hardcoded in the registry, not from user input
        result = subprocess.run(service["command"], shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            flash(f"Success: {service['name']} command executed.", "success")
        else:
            flash(f"Error executing command: {result.stderr}", "danger")
    except Exception as e:
        flash(f"Critical error: {str(e)}", "danger")

    return redirect(url_for("pages.services"))

@bp.route("/services/info/<service_id>")
def service_info(service_id):
    # Find the service
    service = next((s for s in SERVICES if s["id"] == service_id), None)
    if not service:
        return jsonify({"success": False, "message": "Service not found."}), 404

    if platform.system() == "Windows":
        return jsonify({"success": True, "info": "Detailed status is not available on Windows."})

    # Execute systemctl status
    try:
        # Check if it's a systemd service by looking at the restart command
        cmd = ["systemctl", "status", service_id]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        # Even if returncode != 0 (e.g. service stopped), we want the output
        return jsonify({
            "success": True, 
            "info": result.stdout if result.stdout else result.stderr
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@bp.route("/about")
def about():
    return render_template("pages/about.html") 

@bp.route('/printer', methods=['GET', 'POST'])
def printer():
    # print() methods here shows in sever terminal 'sudo journalctl -u API_home_server.service'
    HASHED_PRINTER_PASSWORD = os.getenv("PRINTER_API_KEY") # hashed password hint: ors@
    is_ok_password = False
    if request.method == 'POST': #req from our form!
        # ---  checks ---
        if not HASHED_PRINTER_PASSWORD:
            print("\033[41mServer is not configured for printing. Missing IP or Password environment variable.\033[0m")
            flash("Server is not configured for printing. Missing IP or Password environment variable.", "danger")
            return redirect(request.url)

        user_password = request.form.get("password").strip()
        is_ok_password = check_password_hash(HASHED_PRINTER_PASSWORD, user_password)
        if not user_password or not is_ok_password:
           print("\033[41mInvalid password.\033[0m")
           flash("Invalid password.", "danger")
           return redirect(request.url)
        
        # --- printing Logic ---
        text_to_print = request.form.get('text_to_print')
        file = request.files.get('file_to_print')

        temp_file_path = None
        try:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                temp_file_path = os.path.join("/tmp", filename)
                file.save(temp_file_path)
                success, message = print_file(temp_file_path)
            elif text_to_print:
                temp_file_path = "/tmp/print_job.txt"
                with open(temp_file_path, "w") as f:
                    f.write(text_to_print + "\n\f")
                success, message = print_file(temp_file_path)
            else:
                print("\033[43mNo text or file provided to print.\033[0m")
                flash("No text or file provided to print.", "warning")
                return redirect(request.url)
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

        if success:
            print(f"\033[42mPrint job sent successfully! Message: {message}\033[0m")
            flash(f"Print job sent successfully! Message: {message}", "success")
        else:
            print(f"\033[41mFailed to send print job. Error: {message}\033[0m")
            flash(f"Failed to send print job. Error: {message}", "danger")
        
        return redirect(request.url)
    else: # if I'm just searching ors.strangled.net/printer OR got redirected() i.e( a GET request or done with the form) just give me the page html and dont send any printer commands
        return render_template('pages/printer.html') 
    
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
    # Gather stats
    disk = psutil.disk_usage('/')
    net_io = psutil.net_io_counters()
    sent_speed, recv_speed = get_network_speeds()
    
    os_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "node": platform.node()
    }

    stats = {
        'cpu_percent': psutil.cpu_percent(interval=0.1), # Small interval for accuracy on first call
        'cpu_count': psutil.cpu_count(),
        'memory': psutil.virtual_memory(),
        'disk': disk,
        'net_io': {
            'sent': net_io.bytes_sent,
            'recv': net_io.bytes_recv,
            'sent_speed': sent_speed,
            'recv_speed': recv_speed
        },
        'uptime': int(time.time() - psutil.boot_time()),
        'users': psutil.users(),
        'loadavg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
        'os_info': os_info,
        'process_count': len(psutil.pids()),
        'power_draw': get_power_draw()
    }
    return render_template("pages/server_status.html", stats=stats)

@bp.route("/api/server-stats")
def api_server_stats():
    # Return JSON for auto-refresh
    disk = psutil.disk_usage('/')
    net_io = psutil.net_io_counters()
    sent_speed, recv_speed = get_network_speeds()
    
    mem = psutil.virtual_memory()
    mem_dict = {
        'percent': mem.percent,
        'used': mem.used,
        'total': mem.total
    }
    
    stats = {
        'cpu_percent': psutil.cpu_percent(interval=0.1),
        'memory': mem_dict,
        'disk': {
            'percent': disk.percent,
            'used': disk.used,
            'total': disk.total
        },
        'net_io': {
            'sent': net_io.bytes_sent,
            'recv': net_io.bytes_recv,
            'sent_speed': sent_speed,
            'recv_speed': recv_speed
        },
        'uptime': int(time.time() - psutil.boot_time()),
        'process_count': len(psutil.pids()),
        'power_draw': get_power_draw()
    }
    return jsonify(stats)

@bp.route("/docker-status")
def docker_status():
    containers = get_docker_containers()
    return render_template("pages/docker_status.html", containers=containers)

@bp.route("/ollama-status")
def ollama_status():
    models = get_ollama_models()
    return render_template("pages/ollama_status.html", models=models)
