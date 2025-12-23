"""
统一异常定义
"""

from .errors import (
    AppError,
    ValidationError,
    AudioError,
    ASRError,
    ASREngineNotAvailable,
    ASRFormatError,
    ASRTimeoutError,
    ASRNetworkError,
    AIError,
    AIConnectionError,
    AITimeoutError,
    AIRateLimitError,
    AIInvalidKeyError,
    TTSError,
    TTSVoiceNotFound,
    TTSTimeoutError,
    ConfigError,
    AuthError,
    QuotaExceededError,
)
from .handlers import register_error_handlers

__all__ = [
    'AppError',
    'ValidationError', 
    'AudioError',
    'ASRError',
    'ASREngineNotAvailable',
    'ASRFormatError',
    'ASRTimeoutError',
    'ASRNetworkError',
    'AIError',
    'AIConnectionError',
    'AITimeoutError',
    'AIRateLimitError',
    'AIInvalidKeyError',
    'TTSError',
    'TTSVoiceNotFound',
    'TTSTimeoutError',
    'ConfigError',
    'AuthError',
    'QuotaExceededError',
    'register_error_handlers',
]
