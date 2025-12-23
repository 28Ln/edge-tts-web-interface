"""
原生 WebSocket 实现 (兼容安卓 OkHttp)
"""

import json
from flask import Flask

from ...utils.logger import get_logger
from .socketio import get_vosk_model

logger = get_logger("websocket.native")


def init_native_websocket(app: Flask):
    """初始化原生 WebSocket"""
    try:
        from flask_sock import Sock
    except ImportError:
        logger.warning("flask-sock 未安装，原生 WebSocket 不可用")
        return None
    
    sock = Sock(app)
    
    @sock.route('/ws/realtime')
    def ws_realtime(ws):
        """原生 WebSocket 实时语音识别"""
        logger.info("原生 WebSocket 客户端连接")
        
        model = get_vosk_model()
        recognizer = None
        audio_buffer = bytearray()
        
        tencent_available = False
        try:
            from ...services.asr_service import get_asr_service
            tencent_available = True
        except ImportError:
            pass
        
        if model:
            try:
                from vosk import KaldiRecognizer
                recognizer = KaldiRecognizer(model, 16000)
                ws.send(json.dumps({
                    "type": "status",
                    "connected": True,
                    "engine": "vosk",
                    "message": "已连接，Vosk 实时识别就绪"
                }))
            except ImportError:
                pass
        elif tencent_available:
            ws.send(json.dumps({
                "type": "status",
                "connected": True,
                "engine": "tencent",
                "message": "已连接，使用腾讯云识别"
            }))
        else:
            ws.send(json.dumps({
                "type": "status",
                "connected": True,
                "engine": "none",
                "message": "无可用识别引擎"
            }))
        
        try:
            while True:
                data = ws.receive(timeout=60)
                
                if data is None:
                    break
                
                if isinstance(data, str):
                    try:
                        msg = json.loads(data)
                        action = msg.get("action")
                        
                        if action == "reset":
                            if model and recognizer:
                                from vosk import KaldiRecognizer
                                recognizer = KaldiRecognizer(model, 16000)
                            audio_buffer.clear()
                            ws.send(json.dumps({"type": "status", "message": "识别器已重置"}))
                        
                        elif action == "end":
                            text = ""
                            if recognizer:
                                result = json.loads(recognizer.FinalResult())
                                text = result.get("text", "")
                            elif tencent_available and len(audio_buffer) > 0:
                                asr_service = get_asr_service()
                                text = asr_service.recognize(bytes(audio_buffer), engine="tencent")
                            
                            ws.send(json.dumps({
                                "type": "final",
                                "text": text,
                                "is_end": True
                            }))
                            audio_buffer.clear()
                    except json.JSONDecodeError:
                        pass
                
                elif isinstance(data, bytes):
                    if recognizer:
                        if recognizer.AcceptWaveform(data):
                            result = json.loads(recognizer.Result())
                            text = result.get("text", "")
                            if text:
                                ws.send(json.dumps({"type": "final", "text": text}))
                        else:
                            partial = json.loads(recognizer.PartialResult())
                            text = partial.get("partial", "")
                            if text:
                                ws.send(json.dumps({"type": "partial", "text": text}))
                    else:
                        audio_buffer.extend(data)
        
        except Exception as e:
            logger.info(f"WebSocket 连接断开: {e}")
    
    logger.info("原生 WebSocket 已初始化")
    return sock
