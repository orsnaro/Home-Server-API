from flask import Blueprint, render_template, redirect, abort, jsonify
import psutil
import time

bp = Blueprint("pages", __name__)

@bp.route("/")
def home():
    #return "<a href='http://41.196.252.205:8000/about'> <h1 style='color:orange'> Hello, Home! </h1> </a>"
    #return "<a href='/about'> <h1 style='color:orange'> Hello, Home! </h1> </a>"
    return render_template("pages/home.html")

@bp.route("/about")
def about():
    #return "<a href='http://41.196.252.205:8000/'>  <h1 style='color:purple'>  Hello, About! </h1> </a>"
    return render_template("pages/about.html") 
    
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
    version = "🧙‍♂️"
    with open("/home/ors/repos/Discord_bot_ai/version.txt", "r") as versionFile:
        version = versionFile.read()
        # print(version)
    paylaod = { "schemaVersion": 1, "label": "Hosted Version", "message": version, "color": "#1D63ED" }
    return jsonify(paylaod)
    