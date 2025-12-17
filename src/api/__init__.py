"""
API 路由模块
"""

from flask import Flask, jsonify
from ..exceptions import AppError
from ..utils.logger import setup_logger


def register_error_handlers(app: Flask):
    """注册全局错误处理器"""
    
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        """处理应用异常"""
        return jsonify(error.to_dict()), error.code
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """处理 404"""
        return jsonify({
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "资源不存在",
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """处理 500"""
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        }), 500


def create_app() -> Flask:
    """创建 Flask 应用"""
    from dotenv import load_dotenv
    load_dotenv()
    
    app = Flask(__name__, 
                static_folder='../../static',
                template_folder='../../templates')
    
    # 设置日志
    setup_logger("app")
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册蓝图
    from .mcu import mcu_bp
    app.register_blueprint(mcu_bp)
    
    return app
