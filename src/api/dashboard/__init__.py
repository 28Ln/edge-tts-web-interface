"""
Dashboard 管理面板模块
"""

from flask import Blueprint

# 创建 Blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# 导入路由（避免循环导入）
from . import auth, home, users, api_keys, usage, api

__all__ = ['dashboard_bp']
