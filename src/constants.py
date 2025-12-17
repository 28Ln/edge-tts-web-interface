"""
全局常量定义
消除代码中的魔法数字
"""

# ==================== 音频常量 ====================

# 采样率
SAMPLE_RATE_8K = 8000
SAMPLE_RATE_16K = 16000
SAMPLE_RATE_44K = 44100

# 声道
CHANNELS_MONO = 1
CHANNELS_STEREO = 2

# 采样位宽 (字节)
SAMPLE_WIDTH_8BIT = 1
SAMPLE_WIDTH_16BIT = 2

# 默认音频参数
DEFAULT_SAMPLE_RATE = SAMPLE_RATE_16K
DEFAULT_CHANNELS = CHANNELS_MONO
DEFAULT_SAMPLE_WIDTH = SAMPLE_WIDTH_16BIT

# 音频缓冲区大小
AUDIO_BUFFER_SIZE = 4000
AUDIO_CHUNK_SIZE = 4096


# ==================== API 常量 ====================

# API 版本
API_VERSION_V1 = "1.0.0"
API_VERSION_V2 = "2.0.0"

# 默认分页
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ==================== 配额常量 ====================

# 默认配额
DEFAULT_DAILY_REQUESTS = 1000
DEFAULT_DAILY_TOKENS = 100000
DEFAULT_DAILY_AUDIO_SECONDS = 600  # 10 分钟


# ==================== 会话常量 ====================

# 会话历史
DEFAULT_MAX_HISTORY = 2  # 保留最近几轮对话
MAX_SESSION_MESSAGES = 20


# ==================== 超时常量 ====================

# 请求超时 (秒)
AI_REQUEST_TIMEOUT = 60
ASR_REQUEST_TIMEOUT = 30
TTS_REQUEST_TIMEOUT = 30

# WebSocket 超时
WS_RECEIVE_TIMEOUT = 60


# ==================== 错误码 ====================

class ErrorCode:
    """错误码常量"""
    # 通用错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    
    # 认证错误
    AUTH_FAILED = "AUTH_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    
    # 业务错误
    ASR_ERROR = "ASR_ERROR"
    ASR_ENGINE_UNAVAILABLE = "ASR_ENGINE_UNAVAILABLE"
    ASR_NO_SPEECH = "ASR_NO_SPEECH"
    
    AI_ERROR = "AI_ERROR"
    AI_TIMEOUT = "AI_TIMEOUT"
    
    TTS_ERROR = "TTS_ERROR"
    TTS_VOICE_NOT_FOUND = "TTS_VOICE_NOT_FOUND"
    
    AUDIO_ERROR = "AUDIO_ERROR"
    AUDIO_FORMAT_INVALID = "AUDIO_FORMAT_INVALID"
    AUDIO_EMPTY = "AUDIO_EMPTY"
    
    # 用户错误
    USER_EXISTS = "USER_EXISTS"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_DISABLED = "USER_DISABLED"
    
    # API Key 错误
    API_KEY_INVALID = "API_KEY_INVALID"
    API_KEY_EXPIRED = "API_KEY_EXPIRED"
    API_KEY_REVOKED = "API_KEY_REVOKED"


# ==================== HTTP 状态码映射 ====================

ERROR_CODE_TO_HTTP_STATUS = {
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.METHOD_NOT_ALLOWED: 405,
    
    ErrorCode.AUTH_FAILED: 401,
    ErrorCode.PERMISSION_DENIED: 403,
    ErrorCode.QUOTA_EXCEEDED: 429,
    
    ErrorCode.ASR_ERROR: 500,
    ErrorCode.ASR_ENGINE_UNAVAILABLE: 503,
    ErrorCode.ASR_NO_SPEECH: 400,
    
    ErrorCode.AI_ERROR: 500,
    ErrorCode.AI_TIMEOUT: 504,
    
    ErrorCode.TTS_ERROR: 500,
    ErrorCode.TTS_VOICE_NOT_FOUND: 400,
    
    ErrorCode.AUDIO_ERROR: 500,
    ErrorCode.AUDIO_FORMAT_INVALID: 400,
    ErrorCode.AUDIO_EMPTY: 400,
    
    ErrorCode.USER_EXISTS: 400,
    ErrorCode.USER_NOT_FOUND: 404,
    ErrorCode.USER_DISABLED: 403,
    
    ErrorCode.API_KEY_INVALID: 401,
    ErrorCode.API_KEY_EXPIRED: 401,
    ErrorCode.API_KEY_REVOKED: 401,
}
