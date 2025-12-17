"""
语音合成服务
"""

import os
import subprocess
from typing import Optional

from ..config import get_config
from ..utils.logger import get_tts_logger
from ..exceptions import TTSError

logger = get_tts_logger()


class TTSService:
    """语音合成服务"""
    
    def __init__(self):
        config = get_config()
        self.output_dir = config.tts.output_dir
        self.voices = config.tts.voices
        self.default_voice = config.tts.default_voice
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_voice_name(self, voice_id: str) -> str:
        """获取语音名称"""
        return self.voices.get(voice_id, self.voices.get(self.default_voice))
    
    def synthesize(
        self,
        text: str,
        voice: str = None,
        output_format: str = "wav",
        filename: str = None,
    ) -> str:
        """
        语音合成
        
        Args:
            text: 要合成的文本
            voice: 语音ID
            output_format: 输出格式 (wav/mp3)
            filename: 输出文件名 (不含扩展名)
        
        Returns:
            输出文件路径
        """
        voice = voice or self.default_voice
        voice_name = self.get_voice_name(voice)
        
        if not voice_name:
            raise TTSError(f"未知语音: {voice}")
        
        logger.info(f"[TTS] 合成请求 | text={text[:30]}... | voice={voice}")
        
        # 生成文件名
        if filename is None:
            import time
            filename = f"tts_{int(time.time() * 1000)}"
        
        mp3_path = os.path.join(self.output_dir, f"{filename}.mp3")
        wav_path = os.path.join(self.output_dir, f"{filename}.wav")
        
        try:
            # 使用 edge-tts 生成 MP3
            cmd = ["edge-tts", "--voice", voice_name, "--text", text, "--write-media", mp3_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if output_format == "wav":
                # 转换为 WAV
                subprocess.run([
                    "ffmpeg", "-i", mp3_path,
                    "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
                    "-y", wav_path
                ], capture_output=True, check=True)
                
                # 删除临时 MP3
                if os.path.exists(mp3_path):
                    os.remove(mp3_path)
                
                logger.info(f"[TTS] 合成成功 | path={wav_path}")
                return wav_path
            else:
                logger.info(f"[TTS] 合成成功 | path={mp3_path}")
                return mp3_path
                
        except subprocess.CalledProcessError as e:
            logger.error(f"[TTS] 合成失败: {e}")
            raise TTSError(f"语音合成失败: {e}")
        except Exception as e:
            logger.error(f"[TTS] 合成异常: {e}")
            raise TTSError(f"语音合成异常: {e}")
    
    def get_available_voices(self) -> dict:
        """获取可用语音列表"""
        return self.voices.copy()


# 全局实例
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """获取 TTS 服务实例"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
