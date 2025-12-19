"""
语音合成服务
"""

import os
import time
import subprocess
from typing import Optional, Dict, List

from ..config import get_config
from ..utils.logger import get_tts_logger
from ..exceptions import TTSError, TTSVoiceNotFound, TTSTimeoutError

logger = get_tts_logger()


class TTSService:
    """
    文字转语音（TTS）服务
    
    使用 Microsoft Edge TTS 引擎进行语音合成，支持多种语言和音色。
    
    Attributes:
        output_dir: 输出文件目录
        voices: 可用语音映射表 {voice_id: voice_name}
        default_voice: 默认语音ID
        timeout: TTS 服务超时时间（秒）
        ffmpeg_timeout: FFmpeg 转换超时时间（秒）
        max_retries: 最大重试次数
        retry_delay: 重试延迟时间（秒）
    
    Example:
        >>> service = get_tts_service()
        >>> file_path = service.synthesize("你好世界", voice="xiaoxiao")
        >>> print(f"音频文件: {file_path}")
    """
    
    def __init__(self) -> None:
        config = get_config()
        self.output_dir = config.tts.output_dir
        self.voices = config.tts.voices
        self.default_voice = config.tts.default_voice
        self.timeout = config.tts.timeout
        self.ffmpeg_timeout = config.tts.ffmpeg_timeout
        self.max_retries = config.tts.max_retries
        self.retry_delay = config.tts.retry_delay
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_voice_name(self, voice_id: str) -> Optional[str]:
        """
        获取语音的完整名称
        
        将简短的语音ID转换为 Edge TTS 使用的完整语音名称。
        
        Args:
            voice_id: 语音ID（如 "xiaoxiao", "yunxi"）
        
        Returns:
            完整的语音名称（如 "zh-CN-XiaoxiaoNeural"），
            如果ID不存在则返回默认语音名称
        
        Example:
            >>> service = get_tts_service()
            >>> name = service.get_voice_name("xiaoxiao")
            >>> print(name)  # "zh-CN-XiaoxiaoNeural"
        """
        return self.voices.get(voice_id, self.voices.get(self.default_voice))
    
    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        output_format: str = "wav",
        filename: Optional[str] = None,
    ) -> str:
        """
        将文本合成为语音文件
        
        使用 Edge TTS 引擎将文本转换为语音，支持多种输出格式。
        
        Args:
            text: 要合成的文本内容
            voice: 语音ID（如 "xiaoxiao", "yunxi"），默认使用配置的默认语音
            output_format: 输出格式，支持 "wav" 或 "mp3"，默认为 "wav"
            filename: 输出文件名（不含扩展名），默认自动生成时间戳文件名
        
        Returns:
            生成的音频文件的完整路径
        
        Raises:
            TTSVoiceNotFound: 指定的语音不存在
            TTSTimeoutError: 合成或转换超时
            TTSError: 其他 TTS 服务错误
        
        Example:
            >>> service = get_tts_service()
            >>> # 使用默认语音生成 WAV
            >>> wav_file = service.synthesize("你好世界")
            >>> # 使用指定语音生成 MP3
            >>> mp3_file = service.synthesize("Hello", voice="jenny", output_format="mp3")
        
        Note:
            - MP3 格式由 edge-tts 直接生成
            - WAV 格式需要通过 FFmpeg 转换（16kHz, 单声道, PCM）
            - 超时时间：edge-tts 为 timeout 秒，FFmpeg 为 ffmpeg_timeout 秒
            - 生成的文件保存在 output_dir 目录下
        """
        start_time = time.time()
        voice = voice or self.default_voice
        voice_name = self.get_voice_name(voice)
        
        if not voice_name:
            raise TTSVoiceNotFound(f"未知语音: {voice}")
        
        logger.info(f"[TTS] 合成请求 | text_length={len(text)} | voice={voice} | format={output_format}")
        
        # 生成文件名
        if filename is None:
            filename = f"tts_{int(time.time() * 1000)}"
        
        mp3_path = os.path.join(self.output_dir, f"{filename}.mp3")
        wav_path = os.path.join(self.output_dir, f"{filename}.wav")
        
        try:
            # 使用 edge-tts 生成 MP3
            cmd = ["edge-tts", "--voice", voice_name, "--text", text, "--write-media", mp3_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=self.timeout)
            
            if output_format == "wav":
                # 转换为 WAV
                subprocess.run([
                    "ffmpeg", "-i", mp3_path,
                    "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
                    "-y", wav_path
                ], capture_output=True, check=True, timeout=self.ffmpeg_timeout)
                
                # 删除临时 MP3
                if os.path.exists(mp3_path):
                    try:
                        os.remove(mp3_path)
                    except:
                        pass
                
                duration = (time.time() - start_time) * 1000
                logger.info(f"[TTS] 合成成功 | path={wav_path} | duration={duration:.2f}ms")
                return wav_path
            else:
                duration = (time.time() - start_time) * 1000
                logger.info(f"[TTS] 合成成功 | path={mp3_path} | duration={duration:.2f}ms")
                return mp3_path
                
        except subprocess.TimeoutExpired:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[TTS] 合成超时 | duration={duration:.2f}ms")
            raise TTSTimeoutError("语音合成超时")
            
        except subprocess.CalledProcessError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[TTS] 合成失败 | error={e} | duration={duration:.2f}ms")
            raise TTSError(f"语音合成失败: {e}")
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[TTS] 合成异常 | error={e} | duration={duration:.2f}ms", exc_info=True)
            raise TTSError(f"语音合成异常: {e}")
    
    def get_available_voices(self) -> Dict[str, str]:
        """
        获取所有可用语音的列表
        
        Returns:
            语音映射字典的副本 {voice_id: voice_name}
        
        Example:
            >>> service = get_tts_service()
            >>> voices = service.get_available_voices()
            >>> for voice_id, voice_name in voices.items():
            ...     print(f"{voice_id}: {voice_name}")
        """
        return self.voices.copy()


# 全局实例
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """
    获取 TTS 服务的全局单例实例
    
    使用单例模式确保整个应用只有一个 TTS 服务实例。
    
    Returns:
        TTSService 实例
    
    Example:
        >>> service = get_tts_service()
        >>> file_path = service.synthesize("你好")
    """
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
