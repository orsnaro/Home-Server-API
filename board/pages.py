# =============================================
# File: pages.py
# Version: 1.0.4
# Author: Omar Rashad
# Python Version: 3.13.1 (tags/v3.13.1:0671451, Dec  3 2024, 19:06:28) [MSC v.1942 64 bit (AMD64)]
# Last Update: 2026-05-08
# =============================================
import os
import subprocess
import platform
import glob
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

def run_status_command(command, timeout=5):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return {
            "ok": result.returncode == 0,
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
            "returncode": result.returncode
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"Command not found: {command[0]}",
            "returncode": None
        }
    except Exception as exc:
        return {
            "ok": False,
            "stdout": "",
            "stderr": str(exc),
            "returncode": None
        }


def find_matching_processes(target):
    target_lower = target.casefold()
    matches = []

    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            name = proc.info.get("name") or ""
            exe = proc.info.get("exe") or ""
            cmdline_parts = proc.info.get("cmdline") or []
            cmdline = " ".join(cmdline_parts)

            haystacks = [
                name.casefold(),
                os.path.basename(exe).casefold(),
                cmdline.casefold()
            ]
            if any(target_lower in value for value in haystacks if value):
                matches.append({
                    "pid": proc.info["pid"],
                    "name": name or "Unknown",
                    "exe": exe or "Unknown",
                    "cmdline": cmdline or "N/A"
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return matches


def get_service_process_targets(service):
    if "proc_targets" in service:
        return service["proc_targets"]
    if "proc_name" in service:
        return [service["proc_name"]]
    return []


def get_service_unit_candidates(service):
    candidates = []
    for candidate in service.get("unit_names", []):
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    for candidate in [service.get("id"), service.get("proc_name")]:
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def is_any_systemd_unit_active(unit_candidates):
    if platform.system() == "Windows":
        return False

    for unit in unit_candidates:
        result = run_status_command(["systemctl", "is-active", unit], timeout=3)
        if result["ok"] and result["stdout"] == "active":
            return True
    return False


def get_docker_engine_status() -> bool:
    """
    Docker is considered online when the daemon responds, even with zero containers.
    """
    return run_status_command(["docker", "info"], timeout=5)["ok"]


def get_docker_engine_details():
    result = run_status_command(["docker", "info"], timeout=5)
    return {
        "is_available": result["ok"],
        "message": result["stderr"] or result["stdout"] or "Docker engine is available."
    }

def get_ollama_status() -> bool:
    """
    Ollama is considered online when `ollama list` succeeds.
    """
    return run_status_command(["ollama", "list"], timeout=5)["ok"]


def get_ollama_details():
    result = run_status_command(["ollama", "list"], timeout=5)
    return {
        "is_available": result["ok"],
        "message": result["stderr"] or result["stdout"] or "Ollama is available."
    }

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
        "proc_targets": ["openclaw", "openclaw gateway", "openclaw-gateway"],
        "unit_names": ["openclaw-gateway", "openclaw"],
        "custom_info": True, # Flag to show a 'View Status' button
        "is_protected": False
    },
    {
        "id": "docker",
        "name": "Docker Containers",
        "icon": "🐳",
        "description": "Running docker containers and status.",
        "link": "pages.docker_status",
        "type": "page",
        "custom_check": get_docker_engine_status,
        "is_protected": False
    },
    {
        "id": "ollama",
        "name": "Ollama Models",
        "icon": "🦙",
        "description": "Local LLMs running via Ollama.",
        "link": "pages.ollama_status",
        "type": "page",
        "custom_check": get_ollama_status,
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
last_power_sample = None

def get_docker_containers():
    result = run_status_command(
        ["docker", "ps", "-a", "--format", "{{.ID}}|{{.Names}}|{{.Status}}|{{.Image}}"],
        timeout=5
    )
    if not result["ok"]:
        return [], result["stderr"] or result["stdout"] or "Docker is unavailable."

    containers = []
    for line in result["stdout"].splitlines():
        parts = line.split("|")
        if len(parts) == 4:
            containers.append({
                "id": parts[0],
                "name": parts[1],
                "status": parts[2],
                "image": parts[3]
            })
    return containers, None

def get_ollama_models():
    result = run_status_command(["ollama", "list"], timeout=5)
    if not result["ok"]:
        return [], result["stderr"] or result["stdout"] or "Ollama is unavailable."

    models = []
    lines = result["stdout"].splitlines()
    if len(lines) > 1:
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 1:
                models.append({
                    "name": parts[0],
                    "id": parts[1] if len(parts) > 1 else "N/A",
                    "size": parts[2] if len(parts) > 2 else "N/A",
                    "modified": " ".join(parts[3:]) if len(parts) > 3 else "N/A"
                })
    return models, None

def _read_int_file(path):
    with open(path, "r") as f:
        return int(f.read().strip())


def _read_linux_power_supply_watts():
    try:
        for supply_path in glob.glob("/sys/class/power_supply/*"):
            power_now_path = os.path.join(supply_path, "power_now")
            if os.path.exists(power_now_path):
                return round(_read_int_file(power_now_path) / 1_000_000, 2)

            current_now_path = os.path.join(supply_path, "current_now")
            voltage_now_path = os.path.join(supply_path, "voltage_now")
            if os.path.exists(current_now_path) and os.path.exists(voltage_now_path):
                current_ua = _read_int_file(current_now_path)
                voltage_uv = _read_int_file(voltage_now_path)
                return round((current_ua * voltage_uv) / 1_000_000_000_000, 2)
    except Exception:
        pass

    return None


def _read_linux_hwmon_power_watts():
    total_watts = 0.0
    found = False

    try:
        for hwmon_path in glob.glob("/sys/class/hwmon/hwmon*"):
            for power_path in glob.glob(os.path.join(hwmon_path, "power*_input")):
                microwatts = _read_int_file(power_path)
                total_watts += microwatts / 1_000_000
                found = True
    except Exception:
        pass

    if found:
        return round(total_watts, 2)
    return None


def _read_linux_rapl_power_watts():
    global last_power_sample

    energy_paths = []
    try:
        for rapl_path in glob.glob("/sys/class/powercap/intel-rapl:*"):
            if os.path.basename(rapl_path).count(":") == 1:
                energy_path = os.path.join(rapl_path, "energy_uj")
                max_energy_path = os.path.join(rapl_path, "max_energy_range_uj")
                if os.path.exists(energy_path):
                    energy_paths.append((energy_path, max_energy_path))
    except Exception:
        return None

    if not energy_paths:
        return None

    now = time.time()
    current_energies = {}

    try:
        for energy_path, max_energy_path in energy_paths:
            energy = _read_int_file(energy_path)
            max_energy = _read_int_file(max_energy_path) if os.path.exists(max_energy_path) else None
            current_energies[energy_path] = {"energy": energy, "max_energy": max_energy}
    except Exception:
        return None

    if not last_power_sample:
        last_power_sample = {"time": now, "energies": current_energies}
        return None

    elapsed = now - last_power_sample["time"]
    if elapsed <= 0:
        last_power_sample = {"time": now, "energies": current_energies}
        return None

    total_delta = 0
    for energy_path, sample in current_energies.items():
        previous = last_power_sample["energies"].get(energy_path)
        if previous is None:
            continue

        delta = sample["energy"] - previous["energy"]
        if delta < 0 and sample["max_energy"]:
            delta = (sample["max_energy"] - previous["energy"]) + sample["energy"]

        if delta > 0:
            total_delta += delta

    last_power_sample = {"time": now, "energies": current_energies}
    if total_delta <= 0:
        return None

    return round((total_delta / 1_000_000) / elapsed, 2)


def get_power_draw():
    if platform.system() == "Windows":
        return "N/A"

    direct_power = _read_linux_power_supply_watts()
    if direct_power is not None:
        return f"{direct_power:.2f} W"

    hwmon_power = _read_linux_hwmon_power_watts()
    if hwmon_power is not None:
        return f"{hwmon_power:.2f} W"

    rapl_power = _read_linux_rapl_power_watts()
    if rapl_power is not None:
        return f"{rapl_power:.2f} W"

    try:
        result = subprocess.run(
            ["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "energy-rate:" in line:
                    rate_str = line.split(":")[1].strip().split(" ")[0]
                    return f"{float(rate_str):.2f} W"
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

    # Case 2: Process name and systemd unit checks
    process_targets = get_service_process_targets(service)
    if process_targets:
        if any(find_matching_processes(target) for target in process_targets):
            return True
        if is_any_systemd_unit_active(get_service_unit_candidates(service)):
            return True
    
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

    info_sections = []

    process_targets = get_service_process_targets(service)
    if process_targets:
        matches = []
        for target in process_targets:
            matches.extend(find_matching_processes(target))

        deduped_matches = []
        seen_pids = set()
        for match in matches:
            if match["pid"] in seen_pids:
                continue
            seen_pids.add(match["pid"])
            deduped_matches.append(match)

        if deduped_matches:
            process_lines = [
                f"PID {match['pid']} | {match['name']} | {match['cmdline']}"
                for match in deduped_matches[:5]
            ]
            info_sections.append("Matching processes:\n" + "\n".join(process_lines))

    unit_candidates = get_service_unit_candidates(service)

    try:
        fallback_output = None
        for unit in unit_candidates:
            result = run_status_command(["systemctl", "status", unit, "--no-pager"], timeout=5)
            output = result["stdout"] or result["stderr"]
            if result["ok"] and output:
                info_sections.append(f"systemctl status {unit}:\n{output}")
                break
            if output and fallback_output is None:
                fallback_output = f"systemctl status {unit}:\n{output}"
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    if fallback_output and not any(section.startswith("systemctl status") for section in info_sections):
        info_sections.append(fallback_output)

    if info_sections:
        return jsonify({
            "success": True,
            "info": "\n\n".join(info_sections)
        })

    return jsonify({
        "success": True,
        "info": "No matching process or systemd unit details were found for this service."
    })

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
    if find_matching_processes(wizy_proc_name):
        return "<a href='https://github.com/orsnaro/Discord-Bot-Ai/tree/production-Home-Server'> <h1 style='color:orange'> Wizy Running🧙‍♂️🟢! </h1> </a>"
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
    matches = find_matching_processes(wizy_proc_name)
    return render_template("pages/wizy_status.html", is_running=bool(matches), process_count=len(matches))

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
    docker_details = get_docker_engine_details()
    containers, error_message = get_docker_containers()
    return render_template(
        "pages/docker_status.html",
        containers=containers,
        docker_available=docker_details["is_available"],
        status_message=error_message or docker_details["message"]
    )

@bp.route("/ollama-status")
def ollama_status():
    ollama_details = get_ollama_details()
    models, error_message = get_ollama_models()
    return render_template(
        "pages/ollama_status.html",
        models=models,
        ollama_available=ollama_details["is_available"],
        status_message=error_message or ollama_details["message"]
    )
