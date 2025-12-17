"""
统一日志配置
支持普通格式和 JSON 格式
"""

import os
import sys
import json
import logging
from datetime import datetime


# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FORMAT_JSON = '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志级别映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# 全局日志器缓存
_loggers = {}

# 敏感信息模式
SENSITIVE_PATTERNS = [
    (r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{8,})', r'\1***REDACTED***'),
    (r'(password["\']?\s*[:=]\s*["\']?)([^"\'\s]+)', r'\1***REDACTED***'),
    (r'(secret["\']?\s*[:=]\s*["\']?)([^"\'\s]+)', r'\1***REDACTED***'),
    (r'(token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_.-]{20,})', r'\1***REDACTED***'),
    (r'(sk-[a-zA-Z0-9]{20,})', '***API_KEY***'),
]


class SensitiveFilter(logging.Filter):
    """过滤敏感信息"""
    
    def __init__(self):
        super().__init__()
        import re
        self.patterns = [(re.compile(p, re.IGNORECASE), r) for p, r in SENSITIVE_PATTERNS]
    
    def filter(self, record):
        if record.msg:
            msg = str(record.msg)
            for pattern, replacement in self.patterns:
                msg = pattern.sub(replacement, msg)
            record.msg = msg
        return True


class JsonFormatter(logging.Formatter):
    """JSON 格式化器"""
    
    def format(self, record):
        log_data = {
            "time": self.formatTime(record, LOG_DATE_FORMAT),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # 添加额外字段
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'user'):
            log_data['user'] = record.user
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        
        # 异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(
    name: str = "app",
    level: str = None,
    log_file: str = None,
    json_format: bool = None,
) -> logging.Logger:
    """
    设置日志器
    
    Args:
        name: 日志器名称
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_file: 日志文件路径 (可选)
        json_format: 是否使用 JSON 格式 (默认从环境变量读取)
    
    Returns:
        logging.Logger
    """
    # 从环境变量获取配置
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
    if json_format is None:
        json_format = os.environ.get("LOG_FORMAT", "text").lower() == "json"
    if log_file is None:
        log_file = os.environ.get("LOG_FILE")
    
    log_level = LOG_LEVELS.get(level, logging.INFO)
    
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 选择格式化器
    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    
    # 添加敏感信息过滤器
    logger.addFilter(SensitiveFilter())
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器 (可选)
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 缓存
    _loggers[name] = logger
    
    return logger


def get_logger(name: str = "app") -> logging.Logger:
    """
    获取日志器
    
    Args:
        name: 日志器名称
    
    Returns:
        logging.Logger
    """
    if name in _loggers:
        return _loggers[name]
    return setup_logger(name)


# 预定义的日志器
def get_api_logger():
    """API 日志器"""
    return get_logger("api")


def get_service_logger():
    """服务层日志器"""
    return get_logger("service")


def get_asr_logger():
    """ASR 日志器"""
    return get_logger("asr")


def get_ai_logger():
    """AI 日志器"""
    return get_logger("ai")


def get_tts_logger():
    """TTS 日志器"""
    return get_logger("tts")



# ==================== 结构化日志辅助函数 ====================

def log_with_context(logger, level: str, message: str, **context):
    """
    带上下文的日志记录
    
    Args:
        logger: 日志器
        level: 日志级别 (info/warning/error/debug)
        message: 消息
        **context: 上下文信息 (request_id, user, duration_ms 等)
    """
    # 获取日志方法
    log_method = getattr(logger, level.lower(), logger.info)
    
    # 创建带上下文的记录
    extra = {}
    for key, value in context.items():
        extra[key] = value
    
    # 如果使用 JSON 格式，上下文会自动添加
    # 如果使用文本格式，将上下文附加到消息
    if context:
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        message = f"{message} | {context_str}"
    
    log_method(message, extra=extra)


def log_request(logger, method: str, path: str, status_code: int, duration_ms: float, **context):
    """
    记录请求日志
    
    Args:
        logger: 日志器
        method: HTTP 方法
        path: 请求路径
        status_code: 状态码
        duration_ms: 耗时（毫秒）
        **context: 额外上下文
    """
    log_with_context(
        logger, "info",
        f"{method} {path} {status_code}",
        duration_ms=duration_ms,
        **context
    )


def log_error(logger, error: Exception, **context):
    """
    记录错误日志
    
    Args:
        logger: 日志器
        error: 异常对象
        **context: 上下文信息
    """
    log_with_context(
        logger, "error",
        str(error),
        error_type=type(error).__name__,
        **context
    )
