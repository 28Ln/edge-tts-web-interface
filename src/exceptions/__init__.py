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
]
