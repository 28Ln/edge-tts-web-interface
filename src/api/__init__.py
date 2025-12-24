"""
API 路由模块
"""

import os
from flask import Flask, jsonify, render_template_string
from ..exceptions import AppError
from ..utils.logger import setup_logger, get_logger


def register_error_handlers(app: Flask):
    """注册全局错误处理器"""
    logger = get_logger("error")
    is_debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        logger.warning(f"AppError: {error.error_code} - {error.message}")
        return jsonify(error.to_dict()), error.code
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "资源不存在",
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            "success": False,
            "error_code": "METHOD_NOT_ALLOWED",
            "message": "请求方法不允许",
        }), 405
    
    @app.errorhandler(Exception)
    def handle_generic_error(error):
        logger.error(f"Unhandled exception: {type(error).__name__}: {error}", exc_info=True)
        response = {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        }
        if is_debug:
            response["debug"] = {
                "type": type(error).__name__,
                "message": str(error),
            }
        return jsonify(response), 500


def create_app() -> Flask:
    """创建 Flask 应用"""
    # 确保 .env 已加载（main.py 中已加载，这里是备用）
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    app = Flask(__name__, 
                static_folder='../../static',
                template_folder='../../templates')
    
    # Session 配置（Dashboard 需要）
    app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # 设置日志
    setup_logger("app")
    setup_logger("middleware")
    
    # 注册中间件
    from ..utils.middleware import register_middleware
    register_middleware(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册蓝图
    from .health import health_bp
    from .admin import admin_bp
    from .openapi import openapi_bp
    from .dashboard import dashboard_bp
    from .auth import auth_bp
    from .billing import billing_bp
    
    # v1 API (兼容旧版)
    from .v1.mcu import mcu_bp
    from .v1.wechat import wechat_bp
    
    app.register_blueprint(mcu_bp)        # /mcu/*
    app.register_blueprint(wechat_bp)     # /wechat/*
    app.register_blueprint(health_bp)     # /health/*
    app.register_blueprint(admin_bp)      # /admin/*
    app.register_blueprint(auth_bp)       # /auth/*
    app.register_blueprint(billing_bp)    # /billing/*
    app.register_blueprint(openapi_bp)    # /docs, /openapi.json
    app.register_blueprint(dashboard_bp)  # /dashboard/*
    
    # 注册 v2 API
    from .v2 import register_v2_routes
    v2_bp = register_v2_routes()
    app.register_blueprint(v2_bp)
    
    # 注册 WebSocket
    from .websocket import init_socketio, init_native_websocket, get_realtime_test_page
    
    socketio = init_socketio(app)
    init_native_websocket(app)
    
    # 实时语音识别测试页面
    @app.route('/realtime')
    def realtime_page():
        return render_template_string(get_realtime_test_page())
    
    # 保存 socketio 实例供外部使用
    app.socketio = socketio
    
    return app
