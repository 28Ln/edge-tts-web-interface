"""
数据模型定义
使用 dataclass 定义请求/响应结构
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from datetime import datetime


# ==================== 基础响应 ====================

@dataclass
class BaseResponse:
    """基础响应"""
    success: bool = True
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ErrorResponse(BaseResponse):
    """错误响应"""
    success: bool = False
    error_code: str = "INTERNAL_ERROR"
    message: str = "服务器内部错误"
    details: Optional[str] = None


# ==================== 状态响应 ====================

@dataclass
class StatusResponse(BaseResponse):
    """服务状态响应"""
    asr_engines: Dict[str, bool] = field(default_factory=dict)
    ai: bool = True
    tts: bool = True
    version: str = "2.0.0"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ==================== 语音识别 ====================

@dataclass
class STTRequest:
    """语音识别请求"""
    engine: str = "tencent"
    audio_format: str = "wav"
    sample_rate: int = 16000


@dataclass
class STTResponse(BaseResponse):
    """语音识别响应"""
    text: str = ""
    engine: str = ""
    duration_ms: float = 0


# ==================== 语音合成 ====================

@dataclass
class TTSRequest:
    """语音合成请求"""
    text: str = ""
    voice: str = "xiaoxiao"
    output_format: str = "wav"


# ==================== AI 问答 ====================

@dataclass
class AskRequest:
    """AI 问答请求"""
    question: str = ""
    session: str = "default"


@dataclass
class AskResponse(BaseResponse):
    """AI 问答响应"""
    answer: str = ""
    session: str = ""


# ==================== 语音对话 ====================

@dataclass
class VoiceChatRequest:
    """语音对话请求"""
    engine: str = "tencent"
    audio_format: str = "wav"
    output_type: str = "text"  # text 或 audio
    session: str = "default"


@dataclass
class VoiceChatResponse(BaseResponse):
    """语音对话响应"""
    question: str = ""
    answer: str = ""
    audio_url: Optional[str] = None


# ==================== 工具函数 ====================

def make_response(data: Any = None, **kwargs) -> dict:
    """
    创建标准响应
    
    Args:
        data: 响应数据
        **kwargs: 额外字段
    
    Returns:
        响应字典
    """
    response = {"success": True}
    if data is not None:
        if hasattr(data, 'to_dict'):
            response.update(data.to_dict())
        elif isinstance(data, dict):
            response.update(data)
        else:
            response["data"] = data
    response.update(kwargs)
    return response


def make_error(error_code: str, message: str, details: str = None) -> dict:
    """
    创建错误响应
    
    Args:
        error_code: 错误码
        message: 错误消息
        details: 详细信息
    
    Returns:
        错误响应字典
    """
    response = {
        "success": False,
        "error_code": error_code,
        "message": message,
    }
    if details:
        response["details"] = details
    return response
