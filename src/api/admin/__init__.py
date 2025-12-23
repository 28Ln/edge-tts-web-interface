"""
Admin API 模块
"""

from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 导入路由
from . import routes

__all__ = ['admin_bp']
