"""
Gunicorn entry-point that RealPython’s factory pattern understands.
"""
from board import create_app   # realpython tutorial uses a factory
app = create_app()