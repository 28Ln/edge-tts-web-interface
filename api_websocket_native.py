"""
原生 WebSocket 实时语音识别 API
兼容安卓 OkHttp WebSocket 客户端
"""

import os
import json
import logging
from flask import Blueprint, request
from flask_sock import Sock

logger = logging.getLogger(__name__)

VOSK_MODEL_PATH = "vosk-model-small-cn-0.22"

# 尝试导入 Vosk
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

# 尝试导入腾讯云 ASR
try:
    from tencent_asr.asr_client import TencentASR
    TENCENT_ASR_AVAILABLE = True
except ImportError:
    TENCENT_ASR_AVAILABLE = False

# 全局 Vosk 模型
vosk_model = None

def get_vosk_model():
    """获取或加载 Vosk 模型"""
    global vosk_model
    if vosk_model is None and VOSK_AVAILABLE and os.path.exists(VOSK_MODEL_PATH):
        vosk_model = Model(VOSK_MODEL_PATH)
    return vosk_model


# 全局 Sock 实例
sock = Sock()


def recognize_with_tencent(pcm_data):
    """使用腾讯云识别 PCM 音频数据"""
    import io
    import wave
    import tempfile
    
    if not TENCENT_ASR_AVAILABLE:
        return ""
    
    try:
        # PCM 转 WAV
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm_data)
        wav_data = wav_buffer.getvalue()
        
        # 保存临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.write(wav_data)
        temp_file.close()
        
        # 识别
        asr = TencentASR()
        result = asr.recognize(temp_file.name, voice_format="wav", engine="16k_zh")
        
        # 清理
        import os
        os.unlink(temp_file.name)
        
        if result["success"]:
            return result["text"]
        else:
            logger.error(f"腾讯云识别失败: {result['error']}")
            return ""
    except Exception as e:
        logger.error(f"腾讯云识别异常: {e}")
        return ""

def init_native_websocket(app):
    """初始化原生 WebSocket"""
    sock.init_app(app)
    
    @sock.route('/ws/realtime')
    def ws_realtime(ws):
        """
        原生 WebSocket 实时语音识别端点
        
        连接: ws://IP:3003/ws/realtime
        
        客户端发送:
            - 二进制数据: PCM 16bit 16kHz 音频
            - JSON: {"action": "reset"} 重置识别器
            - JSON: {"action": "end"} 结束识别
        
        服务器返回:
            - {"type": "status", "message": "..."}
            - {"type": "partial", "text": "..."}  中间结果
            - {"type": "final", "text": "..."}    最终结果
            - {"type": "error", "message": "..."}
        """
        logger.info(f"原生 WebSocket 客户端连接")
        
        # 初始化识别器
        model = get_vosk_model()
        recognizer = None
        use_tencent = False  # 是否使用腾讯云识别
        audio_buffer = bytearray()  # 音频缓冲区（腾讯云模式用）
        
        if model:
            recognizer = KaldiRecognizer(model, 16000)
            ws.send(json.dumps({
                "type": "status",
                "connected": True,
                "engine": "vosk",
                "message": "已连接，Vosk 实时识别就绪"
            }))
        elif TENCENT_ASR_AVAILABLE:
            use_tencent = True
            ws.send(json.dumps({
                "type": "status",
                "connected": True,
                "engine": "tencent",
                "message": "已连接，使用腾讯云识别（结束时识别）"
            }))
        else:
            ws.send(json.dumps({
                "type": "status",
                "connected": True,
                "engine": "none",
                "message": "无可用识别引擎"
            }))
        
        audio_count = 0
        total_bytes = 0
        
        try:
            while True:
                data = ws.receive(timeout=60)
                
                if data is None:
                    logger.info(f"📭 [WS] 收到空数据，连接结束")
                    break
                
                # 处理文本消息 (JSON 命令)
                if isinstance(data, str):
                    logger.info(f"📨 [WS] 收到文本消息: {data}")
                    try:
                        msg = json.loads(data)
                        action = msg.get("action")
                        
                        if action == "reset":
                            if model:
                                recognizer = KaldiRecognizer(model, 16000)
                            audio_buffer.clear()
                            logger.info(f"🔄 [WS] 识别器已重置")
                            ws.send(json.dumps({
                                "type": "status",
                                "message": "识别器已重置"
                            }))
                        
                        elif action == "end":
                            logger.info(f"🏁 [WS] 收到结束命令，总共收到 {audio_count} 个音频包，{total_bytes} bytes")
                            
                            text = ""
                            if recognizer:
                                # Vosk 模式
                                result = json.loads(recognizer.FinalResult())
                                text = result.get("text", "")
                                logger.info(f"📝 [WS] Vosk识别结果: '{text}'")
                            elif use_tencent and len(audio_buffer) > 0:
                                # 腾讯云模式 - 将 PCM 转为 WAV 后识别
                                logger.info(f"🔄 [WS] 使用腾讯云识别 {len(audio_buffer)} bytes 音频...")
                                text = recognize_with_tencent(bytes(audio_buffer))
                                logger.info(f"📝 [WS] 腾讯云识别结果: '{text}'")
                            
                            ws.send(json.dumps({
                                "type": "final",
                                "text": text,
                                "is_end": True
                            }))
                            audio_buffer.clear()
                    except json.JSONDecodeError:
                        logger.warning(f"⚠️ [WS] JSON解析失败: {data}")
                
                # 处理二进制消息 (音频数据)
                elif isinstance(data, bytes):
                    audio_count += 1
                    total_bytes += len(data)
                    
                    if audio_count == 1:
                        logger.info(f"🎤 [WS] 开始接收音频数据...")
                    
                    if audio_count % 50 == 0:
                        logger.info(f"📦 [WS] 已收到 {audio_count} 个音频包，共 {total_bytes} bytes")
                    
                    if recognizer:
                        # Vosk 实时识别
                        if recognizer.AcceptWaveform(data):
                            result = json.loads(recognizer.Result())
                            text = result.get("text", "")
                            if text:
                                logger.info(f"📝 [WS] 识别结果(final): '{text}'")
                                ws.send(json.dumps({
                                    "type": "final",
                                    "text": text
                                }))
                        else:
                            partial = json.loads(recognizer.PartialResult())
                            text = partial.get("partial", "")
                            if text:
                                ws.send(json.dumps({
                                    "type": "partial",
                                    "text": text
                                }))
                    elif use_tencent:
                        # 腾讯云模式 - 缓存音频数据
                        audio_buffer.extend(data)
        
        except Exception as e:
            logger.info(f"🔌 [WS] 连接断开: {e} (共收到 {audio_count} 个音频包)")
