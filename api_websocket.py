"""
WebSocket 实时语音识别 API
支持边说边识别，实时返回结果
"""

import os
import io
import wave
import json
import logging
from flask import Blueprint
from flask_socketio import emit
from vosk import Model, KaldiRecognizer

logger = logging.getLogger(__name__)

VOSK_MODEL_PATH = "vosk-model-small-cn-0.22"

# 全局 Vosk 模型 (避免重复加载)
vosk_model = None


def get_vosk_model():
    """获取或加载 Vosk 模型"""
    global vosk_model
    if vosk_model is None and os.path.exists(VOSK_MODEL_PATH):
        vosk_model = Model(VOSK_MODEL_PATH)
    return vosk_model


def register_websocket_handlers(socketio):
    """注册 WebSocket 事件处理器"""
    
    # 存储每个客户端的识别器
    recognizers = {}
    
    @socketio.on('connect', namespace='/realtime')
    def handle_connect():
        """客户端连接"""
        from flask import request
        sid = request.sid
        logger.info(f"WebSocket 客户端连接: {sid}")
        
        model = get_vosk_model()
        if model:
            recognizers[sid] = KaldiRecognizer(model, 16000)
            emit('status', {'connected': True, 'message': '已连接，可以开始说话'})
        else:
            emit('status', {'connected': False, 'message': 'Vosk 模型未找到'})
    
    @socketio.on('disconnect', namespace='/realtime')
    def handle_disconnect():
        """客户端断开"""
        from flask import request
        sid = request.sid
        if sid in recognizers:
            del recognizers[sid]
        logger.info(f"WebSocket 客户端断开: {sid}")
    
    @socketio.on('audio', namespace='/realtime')
    def handle_audio(data):
        """
        接收音频数据并实时识别
        
        客户端发送:
            socketio.emit('audio', audio_bytes)
        
        服务器返回:
            - partial: 中间结果 (说话过程中)
            - final: 最终结果 (一句话结束)
        """
        from flask import request
        sid = request.sid
        
        if sid not in recognizers:
            emit('error', {'message': '识别器未初始化'})
            return
        
        rec = recognizers[sid]
        
        # 处理音频数据
        if isinstance(data, str):
            # Base64 编码的数据
            import base64
            audio_data = base64.b64decode(data)
        else:
            audio_data = data
        
        # 识别
        if rec.AcceptWaveform(audio_data):
            # 一句话结束
            result = json.loads(rec.Result())
            text = result.get('text', '')
            if text:
                emit('final', {'text': text})
        else:
            # 中间结果
            partial = json.loads(rec.PartialResult())
            text = partial.get('partial', '')
            if text:
                emit('partial', {'text': text})
    
    @socketio.on('reset', namespace='/realtime')
    def handle_reset():
        """重置识别器 (开始新的识别)"""
        from flask import request
        sid = request.sid
        
        model = get_vosk_model()
        if model:
            recognizers[sid] = KaldiRecognizer(model, 16000)
            emit('status', {'message': '识别器已重置'})
    
    @socketio.on('end', namespace='/realtime')
    def handle_end():
        """结束识别，获取最终结果"""
        from flask import request
        sid = request.sid
        
        if sid in recognizers:
            rec = recognizers[sid]
            result = json.loads(rec.FinalResult())
            text = result.get('text', '')
            emit('final', {'text': text, 'is_end': True})


def create_websocket_test_page():
    """创建 WebSocket 测试页面 HTML"""
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
let socket;
let mediaRecorder;
let audioContext;
let isRecording = false;

// 连接 WebSocket
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
    
    socket.on('status', (data) => {
        console.log('Status:', data);
    });
    
    socket.on('partial', (data) => {
        document.getElementById('partial').textContent = '识别中: ' + data.text;
    });
    
    socket.on('final', (data) => {
        document.getElementById('partial').textContent = '';
        document.getElementById('final').textContent = data.text;
        
        // 添加到历史
        if (data.text) {
            const history = document.getElementById('history');
            history.innerHTML += '<p>' + data.text + '</p>';
        }
    });
    
    socket.on('error', (data) => {
        console.error('Error:', data);
    });
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        audioContext = new AudioContext({ sampleRate: 16000 });
        const source = audioContext.createMediaStreamSource(stream);
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        
        processor.onaudioprocess = (e) => {
            if (!isRecording) return;
            
            const inputData = e.inputBuffer.getChannelData(0);
            // 转换为 16-bit PCM
            const pcmData = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
                pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
            }
            
            // 发送到服务器
            socket.emit('audio', pcmData.buffer);
        };
        
        source.connect(processor);
        processor.connect(audioContext.destination);
        
        isRecording = true;
        document.getElementById('startBtn').disabled = true;
        document.getElementById('startBtn').classList.add('recording');
        document.getElementById('stopBtn').disabled = false;
        document.getElementById('partial').textContent = '正在录音...';
        
    } catch (err) {
        console.error('录音失败:', err);
        alert('无法访问麦克风: ' + err.message);
    }
}

function stopRecording() {
    isRecording = false;
    
    if (audioContext) {
        audioContext.close();
    }
    
    socket.emit('end');
    
    document.getElementById('startBtn').disabled = false;
    document.getElementById('startBtn').classList.remove('recording');
    document.getElementById('stopBtn').disabled = true;
}

function resetRecognizer() {
    socket.emit('reset');
    document.getElementById('partial').textContent = '等待说话...';
    document.getElementById('final').textContent = '';
}

// 页面加载时连接
connect();
</script>
</body>
</html>
'''
