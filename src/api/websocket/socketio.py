"""
SocketIO WebSocket 实现
"""

import os
import json
from flask import Flask

from ...utils.logger import get_logger

logger = get_logger("websocket.socketio")

VOSK_MODEL_PATH = "vosk-model-small-cn-0.22"
_vosk_model = None


def get_vosk_model():
    """获取或加载 Vosk 模型"""
    global _vosk_model
    if _vosk_model is None:
        try:
            from vosk import Model
            if os.path.exists(VOSK_MODEL_PATH):
                _vosk_model = Model(VOSK_MODEL_PATH)
                logger.info("Vosk 模型已加载")
        except ImportError:
            logger.warning("Vosk 未安装")
    return _vosk_model


def init_socketio(app: Flask):
    """初始化 SocketIO WebSocket"""
    try:
        from flask_socketio import SocketIO, emit
        from vosk import KaldiRecognizer
    except ImportError:
        logger.warning("flask-socketio 或 vosk 未安装，SocketIO 不可用")
        return None
    
    socketio = SocketIO(app, cors_allowed_origins="*")
    recognizers = {}
    
    @socketio.on('connect', namespace='/realtime')
    def handle_connect():
        from flask import request
        sid = request.sid
        logger.info(f"SocketIO 客户端连接: {sid}")
        
        model = get_vosk_model()
        if model:
            recognizers[sid] = KaldiRecognizer(model, 16000)
            emit('status', {'connected': True, 'message': '已连接，可以开始说话'})
        else:
            emit('status', {'connected': False, 'message': 'Vosk 模型未找到'})
    
    @socketio.on('disconnect', namespace='/realtime')
    def handle_disconnect():
        from flask import request
        sid = request.sid
        if sid in recognizers:
            del recognizers[sid]
        logger.info(f"SocketIO 客户端断开: {sid}")
    
    @socketio.on('audio', namespace='/realtime')
    def handle_audio(data):
        from flask import request
        import base64
        
        sid = request.sid
        if sid not in recognizers:
            emit('error', {'message': '识别器未初始化'})
            return
        
        rec = recognizers[sid]
        
        if isinstance(data, str):
            audio_data = base64.b64decode(data)
        else:
            audio_data = data
        
        if rec.AcceptWaveform(audio_data):
            result = json.loads(rec.Result())
            text = result.get('text', '')
            if text:
                emit('final', {'text': text})
        else:
            partial = json.loads(rec.PartialResult())
            text = partial.get('partial', '')
            if text:
                emit('partial', {'text': text})
    
    @socketio.on('reset', namespace='/realtime')
    def handle_reset():
        from flask import request
        sid = request.sid
        model = get_vosk_model()
        if model:
            from vosk import KaldiRecognizer
            recognizers[sid] = KaldiRecognizer(model, 16000)
            emit('status', {'message': '识别器已重置'})
    
    @socketio.on('end', namespace='/realtime')
    def handle_end():
        from flask import request
        sid = request.sid
        if sid in recognizers:
            rec = recognizers[sid]
            result = json.loads(rec.FinalResult())
            text = result.get('text', '')
            emit('final', {'text': text, 'is_end': True})
    
    logger.info("SocketIO WebSocket 已初始化")
    return socketio
