"""
Blueprint package initialization
"""
from .admin import admin_bp
from .api import api_bp
from .auth import auth_bp
from .main import main_bp

__all__ = ["auth_bp", "api_bp", "admin_bp", "main_bp"]
