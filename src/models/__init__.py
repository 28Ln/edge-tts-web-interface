"""
数据模型
"""

from .schemas import (
    BaseResponse,
    ErrorResponse,
    StatusResponse,
    VoiceChatResponse,
    STTRequest,
    TTSRequest,
)

__all__ = [
    'BaseResponse',
    'ErrorResponse',
    'StatusResponse',
    'VoiceChatResponse',
    'STTRequest',
    'TTSRequest',
]
