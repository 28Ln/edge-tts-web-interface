"""
语音识别服务
统一管理 Vosk 和腾讯云 ASR
"""

import os
import io
import wave
import tempfile
import subprocess
from typing import Optional, Tuple
from abc import ABC, abstractmethod

from ..config import get_config
from ..utils.logger import get_asr_logger
from ..exceptions import ASRError, AudioError

logger = get_asr_logger()


class ASREngine(ABC):
    """ASR 引擎抽象基类"""
    
    @abstractmethod
    def recognize(self, audio_data: bytes) -> str:
        """识别音频，返回文本"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass


class VoskEngine(ASREngine):
    """Vosk 本地识别引擎"""
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self._model = None
        self._available = None
    
    def is_available(self) -> bool:
        if self._available is None:
            try:
                from vosk import Model
                if os.path.exists(self.model_path):
                    self._model = Model(self.model_path)
                    self._available = True
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
    """腾讯云 ASR 引擎"""
    
    def __init__(self):
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
    """语音识别服务"""
    
    def __init__(self):
        config = get_config()
        
        # 初始化引擎
        self.engines = {
            "vosk": VoskEngine(config.asr.vosk_model_path),
            "tencent": TencentEngine(),
        }
        self.default_engine = config.asr.default_engine
    
    def get_available_engines(self) -> dict:
        """获取可用引擎状态"""
        return {
            name: engine.is_available()
            for name, engine in self.engines.items()
        }
    
    def convert_to_wav(self, audio_data: bytes) -> bytes:
        """将音频转换为 16kHz 单声道 WAV"""
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
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(temp_output.name):
                with open(temp_output.name, 'rb') as f:
                    wav_data = f.read()
                logger.info(f"[ASR] 转换成功 | wav_size={len(wav_data)}")
                return wav_data
            else:
                raise AudioError(f"音频转换失败: {result.stderr}")
        finally:
            for f in [temp_input.name, temp_output.name]:
                if os.path.exists(f):
                    os.unlink(f)
    
    def recognize(self, audio_data: bytes, engine: str = None, audio_format: str = "wav") -> str:
        """
        语音识别
        
        Args:
            audio_data: 音频数据
            engine: 引擎名称 (vosk/tencent)
            audio_format: 音频格式
        
        Returns:
            识别文本
        """
        engine = engine or self.default_engine
        logger.info(f"[ASR] 识别请求 | engine={engine} | format={audio_format} | size={len(audio_data)}")
        
        # 检查引擎
        if engine not in self.engines:
            raise ASRError(f"未知引擎: {engine}")
        
        asr_engine = self.engines[engine]
        if not asr_engine.is_available():
            raise ASRError(f"引擎不可用: {engine}")
        
        # 转换格式
        if not audio_data.startswith(b'RIFF'):
            audio_data = self.convert_to_wav(audio_data)
        
        # 识别
        text = asr_engine.recognize(audio_data)
        logger.info(f"[ASR] 识别成功 | text={text[:50]}..." if len(text) > 50 else f"[ASR] 识别成功 | text={text}")
        
        return text


# 全局实例
_asr_service: Optional[ASRService] = None


def get_asr_service() -> ASRService:
    """获取 ASR 服务实例"""
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service
