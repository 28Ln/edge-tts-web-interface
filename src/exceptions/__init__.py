"""
统一异常定义
"""

from .errors import (
    AppError,
    ValidationError,
    AudioError,
    ASRError,
    AIError,
    TTSError,
    ConfigError,
)

__all__ = [
    'AppError',
    'ValidationError', 
    'AudioError',
    'ASRError',
    'AIError',
    'TTSError',
    'ConfigError',
]
