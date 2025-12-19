"""
自定义异常类
统一错误码和错误消息
"""

from ..constants import ErrorCode, ERROR_CODE_TO_HTTP_STATUS


class AppError(Exception):
    """应用基础异常"""
    code = 500
    error_code = "INTERNAL_ERROR"
    message = "服务器内部错误"
    
    def __init__(self, message=None, details=None):
        self.message = message or self.__class__.message
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self):
        result = {
            "success": False,
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class ValidationError(AppError):
    """参数验证错误"""
    code = ERROR_CODE_TO_HTTP_STATUS.get(ErrorCode.VALIDATION_ERROR, 400)
    error_code = ErrorCode.VALIDATION_ERROR
    message = "参数验证失败"


class AudioError(AppError):
    """音频处理错误"""
    code = ERROR_CODE_TO_HTTP_STATUS.get(ErrorCode.AUDIO_ERROR, 500)
    error_code = ErrorCode.AUDIO_ERROR
    message = "音频处理失败"


class ASRError(AppError):
    """语音识别错误"""
    code = ERROR_CODE_TO_HTTP_STATUS.get(ErrorCode.ASR_ERROR, 500)
    error_code = ErrorCode.ASR_ERROR
    message = "语音识别失败"


class ASREngineNotAvailable(ASRError):
    """ASR引擎不可用错误"""
    code = 503
    error_code = "ASR_ENGINE_UNAVAILABLE"
    message = "语音识别引擎不可用"


class ASRFormatError(ASRError):
    """ASR音频格式错误"""
    code = 400
    error_code = "ASR_FORMAT_ERROR"
    message = "音频格式不支持"


class ASRTimeoutError(ASRError):
    """ASR识别超时错误"""
    code = 504
    error_code = "ASR_TIMEOUT"
    message = "语音识别超时"


class ASRNetworkError(ASRError):
    """ASR网络错误"""
    code = 503
    error_code = "ASR_NETWORK_ERROR"
    message = "语音识别网络错误"


class AIError(AppError):
    """AI服务错误"""
    code = ERROR_CODE_TO_HTTP_STATUS.get(ErrorCode.AI_ERROR, 500)
    error_code = ErrorCode.AI_ERROR
    message = "AI服务调用失败"


class AIConnectionError(AIError):
    """AI服务连接错误"""
    code = 503
    error_code = "AI_CONNECTION_ERROR"
    message = "AI服务连接失败"


class AITimeoutError(AIError):
    """AI服务超时错误"""
    code = 504
    error_code = "AI_TIMEOUT"
    message = "AI服务请求超时"


class AIRateLimitError(AIError):
    """AI服务速率限制错误"""
    code = 429
    error_code = "AI_RATE_LIMIT"
    message = "AI服务请求过于频繁"


class AIInvalidKeyError(AIError):
    """AI服务密钥无效错误"""
    code = 401
    error_code = "AI_INVALID_KEY"
    message = "AI服务密钥无效"


class TTSError(AppError):
    """语音合成错误"""
    code = ERROR_CODE_TO_HTTP_STATUS.get(ErrorCode.TTS_ERROR, 500)
    error_code = ErrorCode.TTS_ERROR
    message = "语音合成失败"


class TTSVoiceNotFound(TTSError):
    """TTS语音不存在错误"""
    code = 400
    error_code = "TTS_VOICE_NOT_FOUND"
    message = "语音不存在"


class TTSTimeoutError(TTSError):
    """TTS合成超时错误"""
    code = 504
    error_code = "TTS_TIMEOUT"
    message = "语音合成超时"


class ConfigError(AppError):
    """配置错误"""
    code = 500
    error_code = "CONFIG_ERROR"
    message = "配置错误"


class AuthError(AppError):
    """认证错误"""
    code = ERROR_CODE_TO_HTTP_STATUS.get(ErrorCode.AUTH_FAILED, 401)
    error_code = ErrorCode.AUTH_FAILED
    message = "认证失败"


class QuotaExceededError(AppError):
    """配额超限错误"""
    code = ERROR_CODE_TO_HTTP_STATUS.get(ErrorCode.QUOTA_EXCEEDED, 429)
    error_code = ErrorCode.QUOTA_EXCEEDED
    message = "配额已用尽"


# 错误码映射表
ERROR_CODES = {
    # 通用错误 1xxx
    "INTERNAL_ERROR": (500, "服务器内部错误"),
    "VALIDATION_ERROR": (400, "参数验证失败"),
    "NOT_FOUND": (404, "资源不存在"),
    
    # 音频错误 2xxx
    "AUDIO_EMPTY": (400, "音频数据为空"),
    "AUDIO_FORMAT_ERROR": (400, "音频格式错误"),
    "AUDIO_CONVERT_ERROR": (500, "音频转换失败"),
    
    # ASR错误 3xxx
    "ASR_ENGINE_UNAVAILABLE": (503, "语音识别引擎不可用"),
    "ASR_RECOGNIZE_FAILED": (500, "语音识别失败"),
    "ASR_NO_RESULT": (400, "未识别到语音内容"),
    
    # AI错误 4xxx
    "AI_SERVICE_UNAVAILABLE": (503, "AI服务不可用"),
    "AI_REQUEST_FAILED": (500, "AI请求失败"),
    "AI_TIMEOUT": (504, "AI请求超时"),
    
    # TTS错误 5xxx
    "TTS_SERVICE_UNAVAILABLE": (503, "语音合成服务不可用"),
    "TTS_GENERATE_FAILED": (500, "语音合成失败"),
}
