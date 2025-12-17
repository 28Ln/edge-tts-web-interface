"""
统一日志配置
"""

import os
import sys
import logging
from datetime import datetime


# 日志格式
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
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


def setup_logger(
    name: str = "app",
    level: str = None,
    log_file: str = None,
) -> logging.Logger:
    """
    设置日志器
    
    Args:
        name: 日志器名称
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_file: 日志文件路径 (可选)
    
    Returns:
        logging.Logger
    """
    # 从环境变量获取日志级别
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    log_level = LOG_LEVELS.get(level, logging.INFO)
    
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(console_handler)
    
    # 文件处理器 (可选)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
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
