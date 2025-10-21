# =============================================
# File: __init__.py
# Version: 1.0.2-Beta
# Author: Omar Rashad
# Python Version: 3.13.1 (tags/v3.13.1:0671451, Dec  3 2024, 19:06:28) [MSC v.1942 64 bit (AMD64)]
# Last Update: 2025-10-21
# =============================================
from flask import Flask
from board import pages
import os

def create_app():
    app = Flask(__name__)
    app.register_blueprint(pages.bp)
    app.secret_key = os.environ.get("FLASK_WEB_API_KEY")
    return app
