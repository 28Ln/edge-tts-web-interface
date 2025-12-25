"""
语音合成服务
"""

import os
import time
import subprocess
import shutil
import time as _time
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
        rate: Optional[int] = None,
        volume: Optional[int] = None,
    ) -> str:
        def _sapi_synthesize_wav(out_path: str, sapi_rate: Optional[int], sapi_volume: Optional[int]) -> None:
            if os.name != "nt":
                raise TTSError("SAPI TTS 仅支持 Windows")
            if sapi_rate is not None:
                sapi_rate = int(sapi_rate)
                if sapi_rate < -10 or sapi_rate > 10:
                    raise TTSError("SAPI rate 范围为 -10~10")
            if sapi_volume is not None:
                sapi_volume = int(sapi_volume)
                if sapi_volume < 0 or sapi_volume > 100:
                    raise TTSError("SAPI volume 范围为 0~100")
            out_path = os.path.abspath(out_path)
            out_dir = os.path.dirname(out_path)
            os.makedirs(out_dir, exist_ok=True)
            ps_parts = [
                "Add-Type -AssemblyName System.Speech;",
                "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;",
            ]
            if sapi_rate is not None:
                ps_parts.append(f"$s.Rate={sapi_rate};")
            if sapi_volume is not None:
                ps_parts.append(f"$s.Volume={sapi_volume};")
            ps_parts.append(f"$s.SetOutputToWaveFile('{out_path.replace("'", "''")}');")
            ps_parts.append(f"$s.Speak('{text.replace("'", "''")}');")
            ps_parts.append("$s.Dispose();")
            ps = " ".join(ps_parts)
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True,
                text=True,
                check=True,
                timeout=self.timeout,
            )
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

        edge_tts_bin = shutil.which("edge-tts")
        if not edge_tts_bin:
            raise TTSError("找不到 edge-tts 可执行文件（请在后端环境安装：pip install edge-tts，并确保命令行可用）")
        ffmpeg_bin = None
        if output_format == "wav":
            ffmpeg_bin = shutil.which("ffmpeg")
            if not ffmpeg_bin:
                try:
                    import imageio_ffmpeg  # type: ignore

                    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
                    logger.info(f"[TTS] using bundled ffmpeg from imageio-ffmpeg: {ffmpeg_bin}")
                except Exception:
                    ffmpeg_bin = None
        
        # 生成文件名
        if filename is None:
            filename = f"tts_{int(time.time() * 1000)}"
        
        mp3_path = os.path.join(self.output_dir, f"{filename}.mp3")
        wav_path = os.path.join(self.output_dir, f"{filename}.wav")

        mp3_path = os.path.abspath(mp3_path)
        wav_path = os.path.abspath(wav_path)

        proxy_hint = {
            "HTTP_PROXY": os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy"),
            "HTTPS_PROXY": os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"),
            "NO_PROXY": os.environ.get("NO_PROXY") or os.environ.get("no_proxy"),
        }
        if any(proxy_hint.values()):
            logger.info(f"[TTS] proxy env detected: {proxy_hint}")
        edge_proxy = proxy_hint.get("HTTPS_PROXY") or proxy_hint.get("HTTP_PROXY")

        if output_format == "wav" and os.name == "nt":
            try:
                _sapi_synthesize_wav(wav_path, rate, volume)
                duration = (time.time() - start_time) * 1000
                logger.info(f"[TTS] SAPI success | path={wav_path} | duration={duration:.2f}ms")
                return wav_path
            except Exception as e:
                logger.error(f"[TTS] SAPI failed, fallback to edge-tts | error={e}")

        try:
            last_err: Optional[Exception] = None
            attempts = max(1, int(self.max_retries) + 1)
            for attempt in range(1, attempts + 1):
                try:
                    # 使用 edge-tts 生成 MP3
                    cmd = [edge_tts_bin, "--voice", voice_name, "--text", text, "--write-media", mp3_path]
                    if edge_proxy:
                        cmd.extend(["--proxy", edge_proxy])
                    logger.info(f"[TTS] attempt {attempt}/{attempts} exec: {' '.join(cmd[:4])} ... --write-media {mp3_path}")
                    subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=self.timeout)

                    if output_format == "wav":
                        if not ffmpeg_bin:
                            _sapi_synthesize_wav(wav_path, rate, volume)
                            last_err = None
                            break
                        # 转换为 WAV
                        ff_cmd = [
                            ffmpeg_bin, "-i", mp3_path,
                            "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
                            "-y", wav_path,
                        ]
                        subprocess.run(ff_cmd, capture_output=True, check=True, timeout=self.ffmpeg_timeout)
                    last_err = None
                    break
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
                    last_err = e
                    if attempt < attempts:
                        _time.sleep(float(self.retry_delay))
                        continue
                    raise
            if last_err is not None:
                raise last_err
                
            if output_format == "wav":
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
            stderr = (e.stderr or "").strip()
            stdout = (e.stdout or "").strip()
            if stdout:
                logger.error(f"[TTS] stdout: {stdout}")
            if stderr:
                logger.error(f"[TTS] stderr: {stderr}")
            logger.error(f"[TTS] 合成失败 | error={e} | duration={duration:.2f}ms")
            if output_format == "wav" and os.name == "nt":
                try:
                    _sapi_synthesize_wav(wav_path, rate, volume)
                    duration2 = (time.time() - start_time) * 1000
                    logger.info(f"[TTS] SAPI fallback success | path={wav_path} | duration={duration2:.2f}ms")
                    return wav_path
                except Exception as e2:
                    logger.error(f"[TTS] SAPI fallback failed | error={e2}", exc_info=True)
            msg = f"语音合成失败: {e}"
            if stderr:
                msg = f"{msg} | stderr={stderr}"
            raise TTSError(msg)
            
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
