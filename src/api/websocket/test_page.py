"""
WebSocket 测试页面
"""


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
