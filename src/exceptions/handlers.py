"""
全局异常处理器
"""

from flask import jsonify, request
from werkzeug.exceptions import HTTPException

from .errors import AppError
from ..utils.logger import get_logger

logger = get_logger("exception_handler")


def register_error_handlers(app):
    """注册全局异常处理器"""
    
    @app.errorhandler(AppError)
    def handle_app_error(error):
        """处理应用自定义异常"""
        logger.warning(
            f"应用异常: {error.error_code} - {error.message}",
            extra={
                "error_code": error.error_code,
                "path": request.path,
                "method": request.method,
            }
        )
        return jsonify(error.to_dict()), error.code
    
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """处理HTTP异常"""
        logger.warning(
            f"HTTP异常: {error.code} - {error.description}",
            extra={
                "status_code": error.code,
                "path": request.path,
                "method": request.method,
            }
        )
        return jsonify({
            "success": False,
            "error_code": f"HTTP_{error.code}",
            "message": error.description,
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_generic_error(error):
        """处理未捕获的异常"""
        logger.error(
            f"未捕获异常: {type(error).__name__} - {str(error)}",
            exc_info=True,
            extra={
                "path": request.path,
                "method": request.method,
            }
        )
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        }), 500
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        """处理400错误"""
        return jsonify({
            "success": False,
            "error_code": "BAD_REQUEST",
            "message": "请求参数错误",
        }), 400
    
    @app.errorhandler(401)
    def handle_unauthorized(error):
        """处理401错误"""
        return jsonify({
            "success": False,
            "error_code": "UNAUTHORIZED",
            "message": "未授权访问",
        }), 401
    
    @app.errorhandler(403)
    def handle_forbidden(error):
        """处理403错误"""
        return jsonify({
            "success": False,
            "error_code": "FORBIDDEN",
            "message": "禁止访问",
        }), 403
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """处理404错误"""
        return jsonify({
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "资源不存在",
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """处理405错误"""
        return jsonify({
            "success": False,
            "error_code": "METHOD_NOT_ALLOWED",
            "message": "请求方法不允许",
        }), 405
    
    @app.errorhandler(429)
    def handle_too_many_requests(error):
        """处理429错误"""
        return jsonify({
            "success": False,
            "error_code": "TOO_MANY_REQUESTS",
            "message": "请求过于频繁",
        }), 429
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """处理500错误"""
        logger.error(f"500错误: {error}", exc_info=True)
        return jsonify({
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
        }), 500
