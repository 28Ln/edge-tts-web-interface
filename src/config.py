"""
统一配置管理
支持多环境配置 (development/testing/production)
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


# 环境类型
ENV_DEVELOPMENT = "development"
ENV_TESTING = "testing"
ENV_PRODUCTION = "production"


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 3003
    debug: bool = False


@dataclass
class AIConfig:
    """AI 服务配置"""
    api_base: str = ""
    api_key: str = ""
    model: str = "deepseek-r1-search"
    timeout: int = 60
    max_history: int = 2  # 保留最近几轮对话


@dataclass
class ASRConfig:
    """语音识别配置"""
    # 腾讯云
    tencent_secret_id: str = ""
    tencent_secret_key: str = ""
    tencent_appid: str = ""
    # Vosk
    vosk_model_path: str = "vosk-model-small-cn-0.22"
    # 默认引擎
    default_engine: str = "tencent"


@dataclass
class TTSConfig:
    """语音合成配置"""
    output_dir: str = "tts"
    default_voice: str = "xiaoxiao"
    voices: dict = field(default_factory=lambda: {
        "xiaoxiao": "zh-CN-XiaoxiaoNeural",
        "yunxi": "zh-CN-YunxiNeural",
        "xiaoyi": "zh-CN-XiaoyiNeural",
        "yunjian": "zh-CN-YunjianNeural",
    })


@dataclass
class AppConfig:
    """应用总配置"""
    server: ServerConfig = field(default_factory=ServerConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    
    # 目录配置
    upload_dir: str = "uploads"
    log_level: str = "INFO"
    log_format: str = "text"  # text 或 json
    
    # 环境
    env: str = ENV_DEVELOPMENT
    
    # Redis (可选)
    redis_url: str = ""
    
    @property
    def is_production(self) -> bool:
        return self.env == ENV_PRODUCTION
    
    @property
    def is_development(self) -> bool:
        return self.env == ENV_DEVELOPMENT
    
    @property
    def is_testing(self) -> bool:
        return self.env == ENV_TESTING


def load_config(env: str = None) -> AppConfig:
    """
    从环境变量加载配置
    
    Args:
        env: 环境名称，默认从 FLASK_ENV 或 APP_ENV 读取
    """
    config = AppConfig()
    
    # 环境
    if env is None:
        env = os.environ.get("FLASK_ENV") or os.environ.get("APP_ENV", ENV_DEVELOPMENT)
    config.env = env
    
    # 服务器配置
    config.server.port = int(os.environ.get("PORT", 3003))
    config.server.debug = os.environ.get("FLASK_DEBUG", "0") == "1" or env == ENV_DEVELOPMENT
    
    # AI 配置 (支持新旧环境变量名)
    config.ai.api_base = os.environ.get("AI_API_BASE") or os.environ.get("GEMINI_API_BASE", "")
    config.ai.api_key = os.environ.get("AI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    config.ai.model = os.environ.get("AI_MODEL") or os.environ.get("GEMINI_MODEL", "deepseek-r1-search")
    
    # ASR 配置
    config.asr.tencent_secret_id = os.environ.get("TENCENT_SECRET_ID", "")
    config.asr.tencent_secret_key = os.environ.get("TENCENT_SECRET_KEY", "")
    config.asr.tencent_appid = os.environ.get("TENCENT_APPID", "")
    
    # 日志配置
    config.log_level = os.environ.get("LOG_LEVEL", _get_default_log_level(env))
    config.log_format = os.environ.get("LOG_FORMAT", _get_default_log_format(env))
    
    # Redis
    config.redis_url = os.environ.get("REDIS_URL", "")
    
    return config


def _get_default_log_level(env: str) -> str:
    """根据环境获取默认日志级别"""
    defaults = {
        ENV_DEVELOPMENT: "DEBUG",
        ENV_TESTING: "INFO",
        ENV_PRODUCTION: "WARNING",
    }
    return defaults.get(env, "INFO")


def _get_default_log_format(env: str) -> str:
    """根据环境获取默认日志格式"""
    return "json" if env == ENV_PRODUCTION else "text"


def validate_config(config: AppConfig) -> list:
    """
    验证配置，返回错误列表
    """
    errors = []
    
    # AI 配置验证
    if not config.ai.api_base:
        errors.append("缺少 GEMINI_API_BASE 配置")
    if not config.ai.api_key:
        errors.append("缺少 GEMINI_API_KEY 配置")
    
    # ASR 配置验证 (可选，但如果配置了就要完整)
    tencent_configured = any([
        config.asr.tencent_secret_id,
        config.asr.tencent_secret_key,
        config.asr.tencent_appid,
    ])
    if tencent_configured:
        if not config.asr.tencent_secret_id:
            errors.append("缺少 TENCENT_SECRET_ID 配置")
        if not config.asr.tencent_secret_key:
            errors.append("缺少 TENCENT_SECRET_KEY 配置")
        if not config.asr.tencent_appid:
            errors.append("缺少 TENCENT_APPID 配置")
    
    return errors


# 全局配置实例
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = load_config()
    return _config
