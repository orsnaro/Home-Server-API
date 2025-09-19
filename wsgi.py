# =============================================
# File: wsgi.py
# Version: 1.0.0-Beta
# Author: Omar Rashad
# Python Version: 3.13.1 (tags/v3.13.1:0671451, Dec  3 2024, 19:06:28) [MSC v.1942 64 bit (AMD64)]
# Last Update: 2025-05-22
# =============================================
"""
Gunicorn entry-point that RealPython's factory pattern understands.
"""
from board import create_app
app = create_app()
