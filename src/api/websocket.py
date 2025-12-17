"""
WebSocket 实时语音识别 API
支持 SocketIO 和原生 WebSocket
"""

import os
import json
from flask import Flask

from ..utils.logger import get_logger

logger = get_logger("websocket")

VOSK_MODEL_PATH = "vosk-model-small-cn-0.22"

# 全局 Vosk 模型
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


def init_native_websocket(app: Flask):
    """初始化原生 WebSocket (兼容安卓 OkHttp)"""
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
        
        # 尝试导入腾讯云 ASR
        tencent_available = False
        try:
            from ..services.asr_service import get_asr_service
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


def get_realtime_test_page():
    """获取实时语音识别测试页面 HTML"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>实时语音识别测试</title>
    <meta charset="utf-8">
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
        #result { border: 1px solid #ccc; padding: 20px; min-height: 100px; margin: 20px 0; }
        #partial { color: #888; }
        #final { color: #000; font-weight: bold; }
        button { padding: 10px 20px; margin: 5px; cursor: pointer; }
        .recording { background: #ff4444; color: white; }
        #status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .connected { background: #4CAF50; color: white; }
        .disconnected { background: #f44336; color: white; }
    </style>
</head>
<body>
    <h1>🎤 实时语音识别</h1>
    <div id="status" class="disconnected">未连接</div>
    <button id="startBtn" onclick="startRecording()">开始录音</button>
    <button id="stopBtn" onclick="stopRecording()" disabled>停止录音</button>
    <button onclick="resetRecognizer()">重置</button>
    <div id="result">
        <div id="partial">等待说话...</div>
        <div id="final"></div>
    </div>
    <h3>识别历史:</h3>
    <div id="history"></div>
<script>
let socket, audioContext, isRecording = false;
function connect() {
    socket = io('/realtime');
    socket.on('connect', () => {
        document.getElementById('status').textContent = '已连接';
        document.getElementById('status').className = 'connected';
    });
    socket.on('disconnect', () => {
        document.getElementById('status').textContent = '已断开';
        document.getElementById('status').className = 'disconnected';
    });
    socket.on('partial', (data) => {
        document.getElementById('partial').textContent = '识别中: ' + data.text;
    });
    socket.on('final', (data) => {
        document.getElementById('partial').textContent = '';
        document.getElementById('final').textContent = data.text;
        if (data.text) {
            document.getElementById('history').innerHTML += '<p>' + data.text + '</p>';
        }
    });
}
async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContext = new AudioContext({ sampleRate: 16000 });
    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = (e) => {
        if (!isRecording) return;
        const inputData = e.inputBuffer.getChannelData(0);
        const pcmData = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
            pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
        }
        socket.emit('audio', pcmData.buffer);
    };
    source.connect(processor);
    processor.connect(audioContext.destination);
    isRecording = true;
    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
}
function stopRecording() {
    isRecording = false;
    if (audioContext) audioContext.close();
    socket.emit('end');
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
}
function resetRecognizer() {
    socket.emit('reset');
    document.getElementById('partial').textContent = '等待说话...';
    document.getElementById('final').textContent = '';
}
connect();
</script>
</body>
</html>
'''
