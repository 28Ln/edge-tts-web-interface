"""
音频处理工具测试
"""

import io
import wave
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestAudioUtils:
    """音频工具测试"""

    def test_pcm_to_wav(self):
        """测试 PCM 转 WAV"""
        from src.utils.audio import pcm_to_wav, SAMPLE_RATE_16K
        
        # 创建简单的 PCM 数据
        pcm_data = b'\x00\x00' * 1000  # 静音数据
        
        wav_data = pcm_to_wav(pcm_data, sample_rate=SAMPLE_RATE_16K)
        
        # 验证 WAV 格式
        assert wav_data.startswith(b'RIFF')
        assert b'WAVE' in wav_data[:12]
        
        # 验证可以被 wave 模块读取
        wav_buffer = io.BytesIO(wav_data)
        with wave.open(wav_buffer, 'rb') as wf:
            assert wf.getnchannels() == 1
            assert wf.getframerate() == SAMPLE_RATE_16K
            assert wf.getsampwidth() == 2

    def test_is_wav_format(self):
        """测试 WAV 格式检测"""
        from src.utils.audio import is_wav_format
        
        # 有效 WAV 头
        wav_header = b'RIFF\x00\x00\x00\x00WAVEfmt '
        assert is_wav_format(wav_header) is True
        
        # 无效数据
        assert is_wav_format(b'not wav') is False
        assert is_wav_format(b'RIFF') is False

    def test_is_mp3_format(self):
        """测试 MP3 格式检测"""
        from src.utils.audio import is_mp3_format
        
        # MP3 帧同步
        assert is_mp3_format(b'\xff\xfb\x90\x00') is True
        
        # ID3 标签
        assert is_mp3_format(b'ID3\x04\x00\x00') is True
        
        # 无效数据
        assert is_mp3_format(b'not mp3') is False

    def test_get_audio_duration(self):
        """测试获取音频时长"""
        from src.utils.audio import get_audio_duration, pcm_to_wav, SAMPLE_RATE_16K
        
        # 创建 1 秒的 PCM 数据 (16kHz, 16bit, mono)
        one_second_samples = SAMPLE_RATE_16K
        pcm_data = b'\x00\x00' * one_second_samples
        wav_data = pcm_to_wav(pcm_data)
        
        duration = get_audio_duration(wav_data)
        assert abs(duration - 1.0) < 0.01  # 约 1 秒

    def test_get_audio_duration_invalid(self):
        """测试无效音频时长估算"""
        from src.utils.audio import get_audio_duration
        
        # 无效数据会使用估算
        duration = get_audio_duration(b'invalid data')
        assert duration >= 0

    def test_estimate_audio_seconds(self):
        """测试音频秒数估算"""
        from src.utils.audio import estimate_audio_seconds, SAMPLE_RATE_16K, SAMPLE_WIDTH_16BIT
        
        # 1 秒的数据量
        one_second_bytes = SAMPLE_RATE_16K * SAMPLE_WIDTH_16BIT
        
        seconds = estimate_audio_seconds(b'\x00' * one_second_bytes)
        assert abs(seconds - 1.0) < 0.01

    def test_convert_to_wav_already_wav(self):
        """测试已经是 WAV 格式的转换"""
        from src.utils.audio import convert_to_wav, pcm_to_wav, SAMPLE_RATE_16K
        
        # 创建符合要求的 WAV
        pcm_data = b'\x00\x00' * 1000
        wav_data = pcm_to_wav(pcm_data, sample_rate=SAMPLE_RATE_16K, channels=1)
        
        # 应该直接返回原数据
        result = convert_to_wav(wav_data, target_sample_rate=SAMPLE_RATE_16K, target_channels=1)
        assert result == wav_data

    def test_convert_amr_to_wav_error(self):
        """测试 AMR 转换失败"""
        from src.utils.audio import convert_amr_to_wav
        
        with patch('src.utils.audio._ffmpeg_convert') as mock_convert:
            mock_convert.side_effect = Exception('转换失败')
            
            wav_data, error = convert_amr_to_wav(b'fake amr data')
            
            assert wav_data is None
            assert error is not None
            assert '转换失败' in error

    def test_convert_amr_to_wav_success(self):
        """测试 AMR 转换成功"""
        from src.utils.audio import convert_amr_to_wav
        
        with patch('src.utils.audio._ffmpeg_convert') as mock_convert:
            mock_convert.return_value = b'RIFF....WAVEfmt '
            
            wav_data, error = convert_amr_to_wav(b'fake amr data')
            
            assert wav_data is not None
            assert error is None


class TestFFmpegConvert:
    """FFmpeg 转换测试"""

    def test_ffmpeg_convert_success(self):
        """测试 FFmpeg 转换成功"""
        from src.utils.audio import _ffmpeg_convert
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_input = MagicMock()
                mock_input.name = '/tmp/input.audio'
                mock_output = MagicMock()
                mock_output.name = '/tmp/output.wav'
                mock_temp.side_effect = [mock_input, mock_output]
                
                with patch('os.path.exists', return_value=True):
                    with patch('builtins.open', MagicMock(return_value=MagicMock(
                        __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=b'wav_data'))),
                        __exit__=MagicMock()
                    ))):
                        with patch('os.unlink'):
                            result = _ffmpeg_convert(b'audio', 16000, 1)
                            assert result == b'wav_data'

    def test_ffmpeg_convert_failure(self):
        """测试 FFmpeg 转换失败"""
        from src.utils.audio import _ffmpeg_convert
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr='error')
            
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_input = MagicMock()
                mock_input.name = '/tmp/input.audio'
                mock_output = MagicMock()
                mock_output.name = '/tmp/output.wav'
                mock_temp.side_effect = [mock_input, mock_output]
                
                with patch('os.path.exists', return_value=False):
                    with patch('os.unlink'):
                        with pytest.raises(RuntimeError) as exc_info:
                            _ffmpeg_convert(b'audio', 16000, 1)
                        
                        assert 'FFmpeg' in str(exc_info.value)
