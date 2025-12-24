"""
计费 API 模块
"""

from flask import Blueprint

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')

from . import routes

__all__ = ['billing_bp']
