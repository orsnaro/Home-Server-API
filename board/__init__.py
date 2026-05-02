# =============================================
# File: __init__.py
# Version: 1.0.3-Beta
# Author: Omar Rashad
# Python Version: 3.13.1 (tags/v3.13.1:0671451, Dec  3 2024, 19:06:28) [MSC v.1942 64 bit (AMD64)]
# Last Update: 2026-05-02
# =============================================
from flask import Flask
from board import pages
import os
import platform
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

def create_app():
    # In production (Linux), Nginx aliases /static/ to /board/
    # So we need url_for to generate /static/static/...
    # Locally (Windows), we want the standard /static/...
    is_prod = platform.system() == "Linux"
    static_url_path = "/static/static" if is_prod else "/static"
    
    app = Flask(__name__, static_url_path=static_url_path)
    app.register_blueprint(pages.bp)
    app.secret_key = os.environ.get("FLASK_WEB_API_KEY")
    return app
