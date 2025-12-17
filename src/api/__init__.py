"""
API 路由模块
"""

from flask import Flask, jsonify
from ..exceptions import AppError
from ..utils.logger import setup_logger


def register_error_handlers(app: Flask):
    """注册全局错误处理器"""
    import os
    from ..utils.logger import get_logger
    
    logger = get_logger("error")
    is_debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        """处理应用异常"""
        logger.warning(f"AppError: {error.error_code} - {error.message}")
        return jsonify(error.to_dict()), error.code
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """处理 404"""
        return jsonify({
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "资源不存在",
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """处理 405"""
        return jsonify({
            "success": False,
            "error_code": "METHOD_NOT_ALLOWED",
            "message": "请求方法不允许",
        }), 405
    
    @app.errorhandler(Exception)
    def handle_generic_error(error):
        """处理未捕获的异常 - 避免暴露敏感信息"""
        # 记录完整错误到日志
        logger.error(f"Unhandled exception: {type(error).__name__}: {error}", exc_info=True)
        
        # 返回给客户端的信息
        response = {
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        }
        
        # 仅在调试模式下返回详细信息
        if is_debug:
            response["debug"] = {
                "type": type(error).__name__,
                "message": str(error),
            }
        
        return jsonify(response), 500


def create_app() -> Flask:
    """创建 Flask 应用"""
    from dotenv import load_dotenv
    load_dotenv()
    
    app = Flask(__name__, 
                static_folder='../../static',
                template_folder='../../templates')
    
    # 设置日志
    setup_logger("app")
    setup_logger("middleware")
    
    # 注册中间件
    from ..utils.middleware import register_middleware
    register_middleware(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册蓝图
    from .mcu import mcu_bp
    from .health import health_bp
    from .admin import admin_bp
    from .openapi import openapi_bp
    
    app.register_blueprint(mcu_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(openapi_bp)
    
    # 注册 v2 API
    from .v2 import register_v2_routes
    v2_bp = register_v2_routes()
    app.register_blueprint(v2_bp)
    
    return app
