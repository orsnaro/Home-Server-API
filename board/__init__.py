# =============================================
# File: __init__.py
# Version: 1.0.0-Beta
# Author: Omar Rashad
# Python Version: 3.13.1 (tags/v3.13.1:0671451, Dec  3 2024, 19:06:28) [MSC v.1942 64 bit (AMD64)]
# Last Update: 2025-09-20
# =============================================
from flask import Flask
from board import pages

def create_app():
    app = Flask(__name__)
    app.register_blueprint(pages.bp)
    return app
