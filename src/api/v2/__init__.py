"""
API v2 版本
带认证、计费和结构化响应
"""

from flask import Blueprint

# 跟踪是否已注册
_registered = False


def register_v2_routes():
    """注册 v2 路由"""
    global _registered
    
    # 每次创建新的蓝图
    v2_bp = Blueprint('v2', __name__, url_prefix='/v2')
    
    # 导入并注册 mcu 路由
    from .mcu import register_mcu_routes
    register_mcu_routes(v2_bp)
    
    return v2_bp
