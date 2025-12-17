"""
API v1 模块
兼容旧版 API，建议迁移到 v2
"""

from flask import Blueprint

from .mcu import mcu_bp
from .wechat import wechat_bp


def register_v1_routes() -> Blueprint:
    """注册 v1 路由"""
    v1_bp = Blueprint('v1', __name__)
    
    # 注册子蓝图（保持原有路径兼容）
    # /mcu/* 和 /wechat/* 直接在根路径
    
    return v1_bp


__all__ = ['mcu_bp', 'wechat_bp']
