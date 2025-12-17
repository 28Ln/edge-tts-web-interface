"""
音频处理工具函数
统一管理音频格式转换、采样率调整等操作
"""

import os
import io
import wave
import struct
import tempfile
import subprocess
from typing import Optional, Tuple

from .logger import get_logger

logger = get_logger("audio")

# 音频常量
SAMPLE_RATE_16K = 16000
SAMPLE_RATE_8K = 8000
CHANNELS_MONO = 1
SAMPLE_WIDTH_16BIT = 2


def convert_to_wav(
    audio_data: bytes,
    target_sample_rate: int = SAMPLE_RATE_16K,
    target_channels: int = CHANNELS_MONO
) -> bytes:
    """
    将音频数据转换为 WAV 格式
    
    Args:
        audio_data: 原始音频数据
        target_sample_rate: 目标采样率
        target_channels: 目标声道数
    
    Returns:
        WAV 格式音频数据
    """
    # 如果已经是 WAV 格式，检查是否需要转换
    if audio_data.startswith(b'RIFF'):
        try:
            wav_buffer = io.BytesIO(audio_data)
            with wave.open(wav_buffer, 'rb') as wf:
                if wf.getframerate() == target_sample_rate and wf.getnchannels() == target_channels:
                    return audio_data
        except Exception:
            pass
    
    # 使用 FFmpeg 转换
    return _ffmpeg_convert(audio_data, target_sample_rate, target_channels)


def _ffmpeg_convert(
    audio_data: bytes,
    sample_rate: int,
    channels: int
) -> bytes:
    """使用 FFmpeg 转换音频"""
    temp_input = None
    temp_output = None
    
    try:
        temp_input = tempfile.NamedTemporaryFile(suffix='.audio', delete=False)
        temp_input.write(audio_data)
        temp_input.close()
        
        temp_output = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_output.close()
        
        result = subprocess.run([
            "ffmpeg", "-i", temp_input.name,
            "-ac", str(channels),
            "-ar", str(sample_rate),
            "-acodec", "pcm_s16le",
            "-y", temp_output.name
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(temp_output.name):
            with open(temp_output.name, 'rb') as f:
                wav_data = f.read()
            logger.debug(f"音频转换成功 | size={len(wav_data)}")
            return wav_data
        else:
            raise RuntimeError(f"FFmpeg 转换失败: {result.stderr}")
    finally:
        for f in [temp_input, temp_output]:
            if f and os.path.exists(f.name):
                os.unlink(f.name)


def convert_amr_to_wav(amr_data: bytes) -> Tuple[Optional[bytes], Optional[str]]:
    """
    将 AMR 音频转换为 WAV
    
    Args:
        amr_data: AMR 格式音频数据
    
    Returns:
        (wav_data, error_message)
    """
    try:
        wav_data = _ffmpeg_convert(amr_data, SAMPLE_RATE_16K, CHANNELS_MONO)
        return wav_data, None
    except Exception as e:
        logger.error(f"AMR 转换失败: {e}")
        return None, str(e)


def pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = SAMPLE_RATE_16K,
    channels: int = CHANNELS_MONO,
    sample_width: int = SAMPLE_WIDTH_16BIT
) -> bytes:
    """
    将 PCM 数据转换为 WAV 格式
    
    Args:
        pcm_data: PCM 原始数据
        sample_rate: 采样率
        channels: 声道数
        sample_width: 采样位宽 (字节)
    
    Returns:
        WAV 格式数据
    """
    wav_buffer = io.BytesIO()
    
    with wave.open(wav_buffer, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    
    return wav_buffer.getvalue()


def get_audio_duration(audio_data: bytes) -> float:
    """
    获取音频时长（秒）
    
    Args:
        audio_data: WAV 格式音频数据
    
    Returns:
        时长（秒）
    """
    try:
        wav_buffer = io.BytesIO(audio_data)
        with wave.open(wav_buffer, 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / rate
    except Exception:
        # 估算：假设 16kHz 16bit mono
        return len(audio_data) / (SAMPLE_RATE_16K * SAMPLE_WIDTH_16BIT)


def estimate_audio_seconds(audio_data: bytes) -> float:
    """
    估算音频秒数（用于计费）
    
    Args:
        audio_data: 音频数据
    
    Returns:
        估算秒数
    """
    return len(audio_data) / (SAMPLE_RATE_16K * SAMPLE_WIDTH_16BIT)


def is_wav_format(audio_data: bytes) -> bool:
    """检查是否为 WAV 格式"""
    return audio_data.startswith(b'RIFF') and b'WAVE' in audio_data[:12]


def is_mp3_format(audio_data: bytes) -> bool:
    """检查是否为 MP3 格式"""
    return audio_data.startswith(b'\xff\xfb') or audio_data.startswith(b'ID3')
