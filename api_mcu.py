"""
MCU 专用轻量级 API
适用于 ESP32、STM32 等资源受限的单片机设备

接口设计原则：
1. 简单的 HTTP POST 请求
2. 支持原始 PCM/WAV 音频数据
3. 返回纯文本或简单 JSON
4. 最小化数据传输量
5. 支持本地 Vosk 和腾讯云 ASR 双引擎
"""

import os
import io
import wave
import struct
import subprocess
import logging
import tempfile
from flask import Blueprint, request, jsonify, Response, send_file
from vosk import Model, KaldiRecognizer
from openai import OpenAI
import json
import sys

# 创建蓝图
mcu_api = Blueprint('mcu_api', __name__, url_prefix='/mcu')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

VOSK_MODEL_PATH = "vosk-model-small-cn-0.22"
UPLOAD_FOLDER = "uploads"
TTS_FOLDER = "tts"

# 导入腾讯云 ASR
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tencent_asr'))
try:
    from asr_client import TencentASR
    TENCENT_ASR_AVAILABLE = True
    tencent_asr = TencentASR()
    logger.info("腾讯云 ASR 已加载")
except Exception as e:
    TENCENT_ASR_AVAILABLE = False
    tencent_asr = None
    logger.warning(f"腾讯云 ASR 不可用: {e}")

# AI 客户端 (支持环境变量配置)
ai_client = OpenAI(
    base_url=os.environ.get('GEMINI_API_BASE', 'https://vip.sonetto.top/v1'),
    api_key=os.environ.get('GEMINI_API_KEY', 'your_api_key'),
)
AI_MODEL = os.environ.get('GEMINI_MODEL', '[k]gemini-2.5-pro-aistudio-8')

# TTS 语音映射（精简版）
VOICE_MAP = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "yunxi": "zh-CN-YunxiNeural",
}


def pcm_to_wav(pcm_data, sample_rate=16000, channels=1, sample_width=2):
    """将 PCM 原始数据转换为 WAV 格式"""
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    wav_buffer.seek(0)
    return wav_buffer


def speech_to_text_vosk(wav_data):
    """使用本地 Vosk 进行语音识别"""
    if not os.path.exists(VOSK_MODEL_PATH):
        return None, "Vosk 模型未找到"
    
    model = Model(VOSK_MODEL_PATH)
    rec = KaldiRecognizer(model, 16000)
    
    wav_buffer = io.BytesIO(wav_data)
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
        return transcription.strip(), None


def speech_to_text_tencent(wav_data):
    """使用腾讯云 ASR 进行语音识别"""
    if not TENCENT_ASR_AVAILABLE:
        return None, "腾讯云 ASR 未配置"
    
    # 保存临时文件
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.write(wav_data)
        temp_file.close()
        
        result = tencent_asr.recognize(temp_file.name, voice_format="wav", engine="16k_zh")
        
        if result["success"]:
            return result["text"], None
        else:
            return None, result["error"]
    finally:
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


def convert_to_wav_16k(audio_data):
    """将任意音频格式转换为 16kHz 单声道 WAV"""
    temp_input = None
    temp_output = None
    try:
        # 保存输入文件
        temp_input = tempfile.NamedTemporaryFile(suffix='.audio', delete=False)
        temp_input.write(audio_data)
        temp_input.close()
        
        # 输出文件
        temp_output = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_output.close()
        
        # 使用 ffmpeg 转换
        result = subprocess.run([
            "ffmpeg", "-i", temp_input.name,
            "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
            "-y", temp_output.name
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(temp_output.name):
            with open(temp_output.name, 'rb') as f:
                return f.read(), None
        else:
            return None, f"音频转换失败: {result.stderr}"
    except Exception as e:
        return None, str(e)
    finally:
        if temp_input and os.path.exists(temp_input.name):
            os.unlink(temp_input.name)
        if temp_output and os.path.exists(temp_output.name):
            os.unlink(temp_output.name)


def speech_to_text_from_wav(wav_data, engine="vosk"):
    """
    从音频数据进行语音识别 (自动转换格式)
    
    Args:
        wav_data: 音频数据 (支持 WAV/MP3 等格式)
        engine: 识别引擎 "vosk"(本地) 或 "tencent"(腾讯云)
    """
    # 检查是否是有效的 WAV 文件
    if not wav_data.startswith(b'RIFF'):
        # 不是 WAV，尝试转换
        wav_data, error = convert_to_wav_16k(wav_data)
        if error:
            return None, error
    
    if engine == "tencent":
        return speech_to_text_tencent(wav_data)
    else:
        return speech_to_text_vosk(wav_data)


@mcu_api.route('/stt', methods=['POST'])
def mcu_stt():
    """MCU 语音转文字接口"""
    audio_format = request.args.get('format', 'wav')
    sample_rate = int(request.args.get('rate', 16000))
    engine = request.args.get('engine', 'vosk')
    
    logger.info(f"📥 [STT] 收到语音识别请求 | 引擎:{engine} | 格式:{audio_format} | 采样率:{sample_rate}")
    
    try:
        # 获取音频数据
        if request.content_type and 'multipart/form-data' in request.content_type:
            # 文件上传方式
            if 'audio' not in request.files:
                return "错误:未找到音频文件", 400
            audio_data = request.files['audio'].read()
        else:
            # 原始数据方式
            audio_data = request.get_data()
        
        if not audio_data:
            return "错误:音频数据为空", 400
        
        # PCM 转 WAV
        if audio_format == 'pcm':
            wav_buffer = pcm_to_wav(audio_data, sample_rate)
            wav_data = wav_buffer.read()
        else:
            wav_data = audio_data
        
        # 语音识别 (选择引擎)
        text, error = speech_to_text_from_wav(wav_data, engine=engine)
        if error:
            logger.error(f"❌ [STT] 识别失败: {error}")
            return f"错误:{error}", 500
        
        logger.info(f"✅ [STT] 识别成功: {text[:50]}..." if len(text) > 50 else f"✅ [STT] 识别成功: {text}")
        return text, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    except Exception as e:
        logger.error(f"❌ [STT] 异常: {e}")
        return f"错误:{str(e)}", 500


@mcu_api.route('/tts', methods=['POST', 'GET'])
def mcu_tts():
    """MCU 文字转语音接口"""
    if request.method == 'GET':
        text = request.args.get('text', '')
        voice_id = request.args.get('voice', 'xiaoxiao')
        output_format = request.args.get('format', 'wav')
    else:
        data = request.get_json() or {}
        text = data.get('text', '')
        voice_id = data.get('voice', 'xiaoxiao')
        output_format = data.get('format', 'wav')
    
    logger.info(f"📥 [TTS] 收到语音合成请求 | 文字:{text[:30]}... | 语音:{voice_id} | 格式:{output_format}")
    
    if not text:
        return "错误:文字内容为空", 400
    
    voice = VOICE_MAP.get(voice_id, VOICE_MAP['xiaoxiao'])
    
    try:
        temp_mp3 = os.path.join(TTS_FOLDER, "mcu_temp.mp3")
        temp_wav = os.path.join(TTS_FOLDER, "mcu_temp.wav")
        
        cmd = ["edge-tts", "--voice", voice, "--text", text, "--write-media", temp_mp3]
        subprocess.run(cmd, check=True, capture_output=True)
        
        if output_format == 'wav':
            subprocess.run([
                "ffmpeg", "-i", temp_mp3, 
                "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
                "-y", temp_wav
            ], check=True, capture_output=True)
            logger.info(f"✅ [TTS] 语音合成成功")
            return send_file(temp_wav, mimetype='audio/wav')
        else:
            logger.info(f"✅ [TTS] 语音合成成功")
            return send_file(temp_mp3, mimetype='audio/mpeg')
    
    except Exception as e:
        logger.error(f"❌ [TTS] 语音合成失败: {e}")
        return f"错误:{str(e)}", 500


@mcu_api.route('/ask', methods=['POST'])
def mcu_ask():
    """MCU AI 问答接口"""
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json() or {}
        question = data.get('question', '')
    else:
        question = request.get_data(as_text=True)
    
    logger.info(f"📥 [AI] 收到问答请求 | 问题:{question[:50]}..." if len(question) > 50 else f"📥 [AI] 收到问答请求 | 问题:{question}")
    
    if not question:
        return "错误:问题内容为空", 400
    
    try:
        logger.info(f"🤖 [AI] 正在调用AI模型: {AI_MODEL}")
        response = ai_client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {'role': 'system', 'content': '你是一个有帮助的助手，请简洁回答。'},
                {'role': 'user', 'content': question}
            ],
            stream=False
        )
        
        answer = response.choices[0].message.content
        logger.info(f"✅ [AI] 回答成功: {answer[:50]}..." if len(answer) > 50 else f"✅ [AI] 回答成功: {answer}")
        return answer, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    except Exception as e:
        logger.error(f"❌ [AI] 调用失败: {e}")
        return f"错误:{str(e)}", 500


@mcu_api.route('/voice_chat', methods=['POST'])
def mcu_voice_chat():
    """MCU 一站式语音对话接口"""
    audio_format = request.args.get('format', 'wav')
    sample_rate = int(request.args.get('rate', 16000))
    output_type = request.args.get('out', 'audio')
    engine = request.args.get('engine', 'vosk')
    
    logger.info(f"📥 [语音对话] 收到请求 | 引擎:{engine} | 格式:{audio_format} | 输出:{output_type}")
    
    try:
        # 1. 获取音频数据
        if request.content_type and 'multipart/form-data' in request.content_type:
            if 'audio' not in request.files:
                return "错误:未找到音频文件", 400
            audio_data = request.files['audio'].read()
        else:
            audio_data = request.get_data()
        
        if not audio_data:
            return "错误:音频数据为空", 400
        
        logger.info(f"📦 [语音对话] 收到音频数据: {len(audio_data)} bytes")
        
        # 2. PCM 转 WAV
        if audio_format == 'pcm':
            wav_buffer = pcm_to_wav(audio_data, sample_rate)
            wav_data = wav_buffer.read()
        else:
            wav_data = audio_data
        
        # 3. 语音识别
        logger.info(f"🎤 [语音对话] 开始语音识别...")
        question, error = speech_to_text_from_wav(wav_data, engine=engine)
        if error:
            logger.error(f"❌ [语音对话] 识别失败: {error}")
            return f"错误:{error}", 500
        
        if not question:
            return "错误:未识别到语音", 400
        
        logger.info(f"✅ [语音对话] 识别结果: {question}")
        
        # 4. AI 回答
        logger.info(f"🤖 [语音对话] 调用AI...")
        response = ai_client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {'role': 'system', 'content': '你是一个有帮助的助手，请简洁回答，不超过100字。'},
                {'role': 'user', 'content': question}
            ],
            stream=False
        )
        answer = response.choices[0].message.content
        logger.info(f"✅ [语音对话] AI回答: {answer[:50]}..." if len(answer) > 50 else f"✅ [语音对话] AI回答: {answer}")
        
        # 5. 返回结果
        if output_type == 'text':
            return jsonify({"question": question, "answer": answer})
        
        # 生成语音回复
        temp_mp3 = os.path.join(TTS_FOLDER, "mcu_reply.mp3")
        temp_wav = os.path.join(TTS_FOLDER, "mcu_reply.wav")
        
        voice = VOICE_MAP['xiaoxiao']
        subprocess.run([
            "edge-tts", "--voice", voice, "--text", answer, "--write-media", temp_mp3
        ], check=True, capture_output=True)
        
        subprocess.run([
            "ffmpeg", "-i", temp_mp3,
            "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
            "-y", temp_wav
        ], check=True, capture_output=True)
        
        return send_file(temp_wav, mimetype='audio/wav')
    
    except Exception as e:
        logger.error(f"MCU 语音对话错误: {e}")
        return f"错误:{str(e)}", 500


@mcu_api.route('/voice_chat_full', methods=['POST'])
def mcu_voice_chat_full():
    """完整语音对话接口 - 返回识别文字、AI回答、语音URL"""
    import time
    audio_format = request.args.get('format', 'wav')
    sample_rate = int(request.args.get('rate', 16000))
    engine = request.args.get('engine', 'tencent')
    
    logger.info(f"📥 [完整对话] 收到请求 | 引擎:{engine} | 格式:{audio_format}")
    
    try:
        # 1. 获取音频数据
        if request.content_type and 'multipart/form-data' in request.content_type:
            if 'audio' not in request.files:
                return jsonify({"success": False, "error": "未找到音频文件"}), 400
            audio_data = request.files['audio'].read()
        else:
            audio_data = request.get_data()
        
        if not audio_data:
            return jsonify({"success": False, "error": "音频数据为空"}), 400
        
        logger.info(f"📦 [完整对话] 收到音频: {len(audio_data)} bytes")
        
        # 2. PCM 转 WAV
        if audio_format == 'pcm':
            wav_buffer = pcm_to_wav(audio_data, sample_rate)
            wav_data = wav_buffer.read()
        else:
            wav_data = audio_data
        
        # 3. 语音识别
        logger.info(f"🎤 [完整对话] 开始识别...")
        question, error = speech_to_text_from_wav(wav_data, engine=engine)
        if error:
            logger.error(f"❌ [完整对话] 识别失败: {error}")
            return jsonify({"success": False, "error": error}), 500
        
        if not question:
            return jsonify({"success": False, "error": "未识别到语音"}), 400
        
        logger.info(f"✅ [完整对话] 识别结果: {question}")
        
        # 4. AI 回答
        logger.info(f"🤖 [完整对话] 调用AI...")
        response = ai_client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {'role': 'system', 'content': '你是一个有帮助的助手，请简洁回答，不超过100字。'},
                {'role': 'user', 'content': question}
            ],
            stream=False
        )
        answer = response.choices[0].message.content
        logger.info(f"✅ [完整对话] AI回答: {answer[:50]}..." if len(answer) > 50 else f"✅ [完整对话] AI回答: {answer}")
        
        # 5. 尝试生成语音文件 (TTS 失败不影响返回文字结果)
        timestamp = int(time.time() * 1000)
        audio_filename = f"reply_{timestamp}.wav"
        temp_mp3 = os.path.join(TTS_FOLDER, f"reply_{timestamp}.mp3")
        temp_wav = os.path.join(TTS_FOLDER, audio_filename)
        audio_url = None
        
        try:
            voice = VOICE_MAP['xiaoxiao']
            subprocess.run([
                "edge-tts", "--voice", voice, "--text", answer, "--write-media", temp_mp3
            ], check=True, capture_output=True)
            
            subprocess.run([
                "ffmpeg", "-i", temp_mp3,
                "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
                "-y", temp_wav
            ], check=True, capture_output=True)
            
            audio_url = f"/mcu/audio/{audio_filename}"
        except Exception as tts_error:
            logger.warning(f"TTS 生成失败 (不影响文字返回): {tts_error}")
        
        # 清理 mp3
        if os.path.exists(temp_mp3):
            os.remove(temp_mp3)
        
        return jsonify({
            "success": True,
            "question": question,
            "answer": answer,
            "audio_url": audio_url,
            "tts_available": audio_url is not None
        })
    
    except Exception as e:
        logger.error(f"完整语音对话错误: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@mcu_api.route('/audio/<filename>')
def mcu_audio(filename):
    """获取生成的音频文件"""
    return send_file(os.path.join(TTS_FOLDER, filename), mimetype='audio/wav')


@mcu_api.route('/ask_stream', methods=['POST'])
def mcu_ask_stream():
    """
    AI 流式问答接口 - 实时返回 AI 回答
    
    请求方式: POST
    Content-Type: text/plain 或 application/json
    
    返回: text/event-stream (SSE 格式)
    
    示例响应:
        data: 你好
        data: ！
        data: 有什么
        data: 可以帮你的？
        data: [DONE]
    """
    if request.content_type and 'application/json' in request.content_type:
        data = request.get_json() or {}
        question = data.get('question', '')
    else:
        question = request.get_data(as_text=True)
    
    if not question:
        return "错误:问题内容为空", 400
    
    def generate():
        try:
            response = ai_client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {'role': 'system', 'content': '你是一个有帮助的助手，请简洁回答。'},
                    {'role': 'user', 'content': question}
                ],
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield f"data: {content}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@mcu_api.route('/ping', methods=['GET'])
def mcu_ping():
    """
    MCU 连接测试接口
    返回: "pong"
    """
    return "pong", 200


@mcu_api.route('/status', methods=['GET'])
def mcu_status():
    """
    查看 MCU API 状态和可用引擎
    
    返回 JSON:
    {
        "vosk": true/false,      # 本地 Vosk 是否可用
        "tencent": true/false,   # 腾讯云 ASR 是否可用
        "ai": true,              # AI 问答是否可用
        "tts": true              # TTS 是否可用
    }
    """
    vosk_available = os.path.exists(VOSK_MODEL_PATH)
    
    return jsonify({
        "vosk": vosk_available,
        "tencent": TENCENT_ASR_AVAILABLE,
        "ai": True,
        "tts": True,
        "engines": {
            "vosk": "本地离线识别，速度快，准确率一般",
            "tencent": "腾讯云在线识别，准确率高，需要网络"
        }
    })
