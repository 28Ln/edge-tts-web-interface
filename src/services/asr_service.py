"""
语音识别服务
统一管理 Vosk 和腾讯云 ASR
"""

import os
import io
import wave
import time
import tempfile
import subprocess
from typing import Optional, Tuple, Dict, Any
from abc import ABC, abstractmethod

from ..config import get_config
from ..utils.logger import get_asr_logger
from ..exceptions import (
    ASRError, 
    ASREngineNotAvailable, 
    ASRFormatError, 
    ASRTimeoutError,
    ASRNetworkError,
    AudioError
)

logger = get_asr_logger()


class ASREngine(ABC):
    """
    ASR 引擎抽象基类
    
    定义所有 ASR 引擎必须实现的接口，支持多种识别引擎的统一管理。
    
    Note:
        所有继承此类的引擎都必须实现 recognize 和 is_available 方法。
    """
    
    @abstractmethod
    def recognize(self, audio_data: bytes) -> str:
        """
        识别音频并返回文本
        
        Args:
            audio_data: WAV 格式的音频数据（16kHz, 单声道, PCM）
        
        Returns:
            识别出的文本内容
        
        Raises:
            ASRError: 识别失败
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        检查引擎是否可用
        
        Returns:
            True 表示引擎可用，False 表示不可用
        
        Note:
            - Vosk 引擎需要模型文件存在
            - 腾讯云引擎需要配置密钥
        """
        pass


class VoskEngine(ASREngine):
    """
    Vosk 本地语音识别引擎
    
    使用 Vosk 进行离线语音识别，无需网络连接，完全免费。
    
    Attributes:
        model_path: Vosk 模型文件路径
        _model: Vosk 模型实例（延迟加载）
        _available: 引擎可用性缓存
    
    Example:
        >>> engine = VoskEngine("vosk-model-small-cn-0.22")
        >>> if engine.is_available():
        ...     text = engine.recognize(audio_data)
    
    Note:
        - 需要安装 vosk 包：pip install vosk
        - 需要下载模型文件：https://alphacephei.com/vosk/models
        - 支持中文、英文等多种语言
    """
    
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self._model = None
        self._available = None
    
    def is_available(self) -> bool:
        if self._available is None:
            try:
                from vosk import Model
                if os.path.exists(self.model_path):
                    try:
                        self._model = Model(self.model_path)
                        self._available = True
                    except Exception as e:
                        logger.warning(f"[ASR] Vosk 模型加载失败，标记为不可用 | path={self.model_path} | error={e}")
                        self._model = None
                        self._available = False
                else:
                    self._available = False
            except ImportError:
                self._available = False
        return self._available
    
    def recognize(self, audio_data: bytes) -> str:
        if not self.is_available():
            raise ASRError("Vosk 模型未安装")
        
        import json
        from vosk import KaldiRecognizer
        
        rec = KaldiRecognizer(self._model, 16000)
        
        wav_buffer = io.BytesIO(audio_data)
        with wave.open(wav_buffer, "rb") as wf:
            transcription = ""
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result()).get("text", "")
                    transcription += result
            
            final_result = json.loads(rec.FinalResult()).get("text", "")
            transcription += final_result
            
        return transcription.strip()


class TencentEngine(ASREngine):
    """
    腾讯云语音识别引擎
    
    使用腾讯云 ASR 服务进行在线语音识别，识别准确率高。
    
    Attributes:
        _client: 腾讯云 ASR 客户端实例（延迟加载）
    
    Example:
        >>> engine = TencentEngine()
        >>> if engine.is_available():
        ...     text = engine.recognize(audio_data)
    
    Note:
        - 需要配置腾讯云密钥（TENCENT_SECRET_ID, TENCENT_SECRET_KEY）
        - 需要网络连接
        - 可能产生费用
    """
    
    def __init__(self) -> None:
        self._client = None
    
    def is_available(self) -> bool:
        if self._client is None:
            from .asr.tencent import TencentASR
            self._client = TencentASR()
        return self._client.is_available()
    
    def recognize(self, audio_data: bytes) -> str:
        if not self.is_available():
            raise ASRError("腾讯云 ASR 未配置")
        
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        try:
            temp_file.write(audio_data)
            temp_file.close()
            
            result = self._client.recognize(temp_file.name, voice_format="wav", engine="16k_zh")
            
            if result["success"]:
                return result["text"]
            else:
                raise ASRError(result["error"])
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)


class ASRService:
    """
    语音识别服务
    
    统一管理多种 ASR 引擎（Vosk、腾讯云），提供语音识别功能。
    
    Attributes:
        engines: 可用的 ASR 引擎字典 {engine_name: engine_instance}
        default_engine: 默认使用的引擎名称
        timeout: ASR 服务超时时间（秒）
        convert_timeout: 音频转换超时时间（秒）
        max_retries: 最大重试次数
        retry_delay: 重试延迟时间（秒）
    
    Example:
        >>> service = get_asr_service()
        >>> text = service.recognize(audio_data, engine="tencent")
        >>> print(f"识别结果: {text}")
    
    Note:
        - 自动进行音频格式转换（转为 16kHz 单声道 WAV）
        - 支持多种音频格式输入
        - 引擎不可用时自动抛出异常
    """
    
    def __init__(self) -> None:
        config = get_config()
        
        # 初始化引擎
        self.engines = {
            "vosk": VoskEngine(config.asr.vosk_model_path),
            "tencent": TencentEngine(),
        }
        self.default_engine = config.asr.default_engine
        self.timeout = config.asr.timeout
        self.convert_timeout = config.asr.convert_timeout
        self.max_retries = config.asr.max_retries
        self.retry_delay = config.asr.retry_delay
    
    def get_available_engines(self) -> Dict[str, bool]:
        """
        获取所有引擎的可用状态
        
        Returns:
            引擎可用性字典 {engine_name: is_available}
        
        Example:
            >>> service = get_asr_service()
            >>> engines = service.get_available_engines()
            >>> print(engines)  # {"vosk": False, "tencent": True}
        """
        return {
            name: engine.is_available()
            for name, engine in self.engines.items()
        }
    
    def convert_to_wav(self, audio_data: bytes) -> bytes:
        """
        将音频转换为标准 WAV 格式
        
        使用 FFmpeg 将任意格式的音频转换为 16kHz 单声道 PCM WAV 格式，
        这是大多数 ASR 引擎要求的标准格式。
        
        Args:
            audio_data: 原始音频数据（任意格式）
        
        Returns:
            转换后的 WAV 格式音频数据
        
        Raises:
            ASRTimeoutError: 转换超时
            AudioError: 转换失败
        
        Example:
            >>> service = get_asr_service()
            >>> mp3_data = open("audio.mp3", "rb").read()
            >>> wav_data = service.convert_to_wav(mp3_data)
        
        Note:
            - 输出格式：16kHz, 单声道, PCM 16-bit
            - 超时时间为 convert_timeout 秒（默认30秒）
            - 需要系统安装 FFmpeg
        """
        start_time = time.time()
        logger.info(f"[ASR] 转换音频 | size={len(audio_data)}")
        
        temp_input = tempfile.NamedTemporaryFile(suffix='.audio', delete=False)
        temp_output = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        
        try:
            temp_input.write(audio_data)
            temp_input.close()
            temp_output.close()
            
            result = subprocess.run([
                "ffmpeg", "-i", temp_input.name,
                "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
                "-y", temp_output.name
            ], capture_output=True, text=True, timeout=self.convert_timeout)
            
            if result.returncode == 0 and os.path.exists(temp_output.name):
                with open(temp_output.name, 'rb') as f:
                    wav_data = f.read()
                duration = (time.time() - start_time) * 1000
                logger.info(f"[ASR] 转换成功 | wav_size={len(wav_data)} | duration={duration:.2f}ms")
                return wav_data
            else:
                raise AudioError(f"音频转换失败: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[ASR] 转换超时 | duration={duration:.2f}ms")
            raise ASRTimeoutError("音频转换超时")
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[ASR] 转换失败 | error={e} | duration={duration:.2f}ms")
            raise
            
        finally:
            for f in [temp_input.name, temp_output.name]:
                if os.path.exists(f):
                    try:
                        os.unlink(f)
                    except:
                        pass
    
    def recognize(self, audio_data: bytes, engine: Optional[str] = None, audio_format: str = "wav") -> str:
        """
        语音识别
        
        将音频数据转换为文本，支持多种引擎和音频格式。
        
        Args:
            audio_data: 音频数据（字节流）
            engine: 引擎名称（"vosk" 或 "tencent"），默认使用配置的默认引擎
            audio_format: 音频格式提示（用于日志），实际会自动检测和转换
        
        Returns:
            识别出的文本内容
        
        Raises:
            ASRError: 未知引擎或识别失败
            ASREngineNotAvailable: 引擎不可用
            ASRFormatError: 音频格式转换失败
        
        Example:
            >>> service = get_asr_service()
            >>> # 使用默认引擎
            >>> text = service.recognize(audio_data)
            >>> # 指定引擎
            >>> text = service.recognize(audio_data, engine="tencent")
            >>> print(f"识别结果: {text}")
        
        Note:
            - 自动检测音频格式（通过 RIFF 头）
            - 非 WAV 格式自动转换
            - 记录详细的识别日志
            - 超时时间为 timeout 秒（默认60秒）
        """
        start_time = time.time()
        engine = engine or self.default_engine
        logger.info(f"[ASR] 识别请求 | engine={engine} | format={audio_format} | size={len(audio_data)}")
        
        try:
            # 检查引擎
            if engine not in self.engines:
                raise ASRError(f"未知引擎: {engine}")
            
            asr_engine = self.engines[engine]
            if not asr_engine.is_available():
                raise ASREngineNotAvailable(f"引擎不可用: {engine}")
            
            # 转换格式
            if not audio_data.startswith(b'RIFF'):
                try:
                    audio_data = self.convert_to_wav(audio_data)
                except Exception as e:
                    logger.error(f"[ASR] 格式转换失败 | error={e}")
                    raise ASRFormatError(f"音频格式转换失败: {e}")
            
            # 识别
            text = asr_engine.recognize(audio_data)
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"[ASR] 识别成功 | text_length={len(text)} | duration={duration:.2f}ms")
            
            return text
            
        except ASREngineNotAvailable:
            raise
        except ASRFormatError:
            raise
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[ASR] 识别失败 | error={e} | duration={duration:.2f}ms", exc_info=True)
            raise ASRError(f"语音识别失败: {e}")


# 全局实例
_asr_service: Optional[ASRService] = None


def get_asr_service() -> ASRService:
    """
    获取 ASR 服务的全局单例实例
    
    使用单例模式确保整个应用只有一个 ASR 服务实例，
    避免重复初始化引擎和模型。
    
    Returns:
        ASRService 实例
    
    Example:
        >>> service = get_asr_service()
        >>> text = service.recognize(audio_data)
    
    Note:
        - 首次调用时会初始化所有引擎
        - 后续调用返回同一实例
    """
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service
