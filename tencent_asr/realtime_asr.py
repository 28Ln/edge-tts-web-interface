# 腾讯云实时语音识别（WebSocket 流式）
import base64
import hashlib
import hmac
import json
import time
import threading
import wave
import pyaudio
from datetime import datetime
from urllib.parse import urlencode
import websocket

from config import TENCENT_SECRET_ID, TENCENT_SECRET_KEY, TENCENT_APPID


class RealtimeASR:
    """腾讯云实时语音识别 - WebSocket 流式"""
    
    def __init__(self, engine: str = "16k_zh_en"):
        """
        Args:
            engine: 引擎类型
                - 16k_zh_en: 中英文混合（默认）
                - 16k_zh: 中文普通话
                - 16k_en: 纯英文
        """
        self.secret_id = TENCENT_SECRET_ID
        self.secret_key = TENCENT_SECRET_KEY
        self.appid = TENCENT_APPID
        self.engine = engine
        
        # 音频参数
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 3200  # 每次发送的音频帧大小 (100ms)
        
        # 状态
        self.ws = None
        self.is_recording = False
        self.full_text = ""
        self.current_text = ""
        
        # 回调函数
        self.on_result = None  # 识别结果回调
        self.on_final = None   # 最终结果回调
    
    def _generate_sign(self, params: dict) -> str:
        """生成签名"""
        sorted_params = sorted(params.items())
        query_string = urlencode(sorted_params)
        sign_str = f"asr.cloud.tencent.com/asr/v2/{self.appid}?{query_string}"
        
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha1
        ).digest()
        
        return base64.b64encode(signature).decode("utf-8")
    
    def _get_ws_url(self) -> str:
        """生成 WebSocket 连接 URL"""
        timestamp = int(time.time())
        expired = timestamp + 86400  # 24小时有效
        nonce = timestamp
        
        params = {
            "secretid": self.secret_id,
            "timestamp": timestamp,
            "expired": expired,
            "nonce": nonce,
            "engine_model_type": self.engine,
            "voice_id": f"voice_{timestamp}",
            "voice_format": 1,  # PCM
            "needvad": 1,       # 开启 VAD
            "filter_dirty": 1,  # 过滤脏词
            "filter_modal": 1,  # 过滤语气词
            "convert_num_mode": 1,  # 数字转换
        }
        
        signature = self._generate_sign(params)
        params["signature"] = signature
        
        query_string = urlencode(params)
        return f"wss://asr.cloud.tencent.com/asr/v2/{self.appid}?{query_string}"

    def _on_message(self, ws, message):
        """处理服务器消息"""
        try:
            data = json.loads(message)
            code = data.get("code", -1)
            
            if code != 0:
                print(f"[错误] {data.get('message', '未知错误')}")
                return
            
            result = data.get("result", {})
            voice_text_str = result.get("voice_text_str", "")
            slice_type = result.get("slice_type", 0)
            
            # slice_type: 0=一段话开始, 1=一段话中间, 2=一段话结束
            if slice_type == 2:
                # 一句话结束，更新完整文本
                self.full_text += voice_text_str
                self.current_text = ""
                if self.on_final:
                    self.on_final(voice_text_str, self.full_text)
            else:
                # 中间结果
                self.current_text = voice_text_str
                if self.on_result:
                    self.on_result(voice_text_str, False)
                    
        except json.JSONDecodeError:
            print(f"[错误] 无法解析消息: {message}")
    
    def _on_error(self, ws, error):
        """处理错误"""
        print(f"[WebSocket 错误] {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """连接关闭"""
        print("[WebSocket] 连接已关闭")
        self.is_recording = False
    
    def _on_open(self, ws):
        """连接建立"""
        print("[WebSocket] 连接已建立，开始录音...")
        self.is_recording = True
        
        # 启动录音线程
        threading.Thread(target=self._record_and_send, daemon=True).start()
    
    def _record_and_send(self):
        """录音并发送音频数据"""
        p = pyaudio.PyAudio()
        
        stream = p.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        print("[录音] 开始录音，按 Ctrl+C 停止...")
        
        try:
            while self.is_recording:
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                if self.ws and self.is_recording:
                    self.ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
        except Exception as e:
            print(f"[录音错误] {e}")
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # 发送结束标志
            if self.ws:
                end_msg = json.dumps({"type": "end"})
                self.ws.send(end_msg)
    
    def start(self, on_result=None, on_final=None):
        """
        开始实时语音识别
        
        Args:
            on_result: 中间结果回调 fn(text, is_final)
            on_final: 最终结果回调 fn(sentence, full_text)
        """
        self.on_result = on_result
        self.on_final = on_final
        self.full_text = ""
        self.current_text = ""
        
        url = self._get_ws_url()
        
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        self.ws.run_forever()
    
    def stop(self):
        """停止识别"""
        self.is_recording = False
        if self.ws:
            self.ws.close()

    def recognize_file(self, audio_path: str, on_result=None, on_final=None) -> str:
        """
        识别音频文件（流式方式）
        
        Args:
            audio_path: WAV 音频文件路径 (16kHz, 单声道, 16bit)
            on_result: 中间结果回调
            on_final: 最终结果回调
        
        Returns:
            完整识别文本
        """
        self.on_result = on_result
        self.on_final = on_final
        self.full_text = ""
        
        url = self._get_ws_url()
        
        # 同步方式处理文件
        ws = websocket.create_connection(url)
        
        try:
            with wave.open(audio_path, "rb") as wf:
                while True:
                    data = wf.readframes(self.chunk_size)
                    if not data:
                        break
                    ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
                    
                    # 接收结果
                    try:
                        ws.settimeout(0.1)
                        result = ws.recv()
                        self._process_result(result)
                    except websocket.WebSocketTimeoutException:
                        pass
            
            # 发送结束标志
            ws.send(json.dumps({"type": "end"}))
            
            # 接收剩余结果
            ws.settimeout(5)
            while True:
                try:
                    result = ws.recv()
                    self._process_result(result)
                except websocket.WebSocketTimeoutException:
                    break
                except websocket.WebSocketConnectionClosedException:
                    break
                    
        finally:
            ws.close()
        
        return self.full_text
    
    def _process_result(self, message):
        """处理识别结果"""
        try:
            data = json.loads(message)
            if data.get("code") == 0:
                result = data.get("result", {})
                voice_text_str = result.get("voice_text_str", "")
                slice_type = result.get("slice_type", 0)
                
                if slice_type == 2:
                    self.full_text += voice_text_str
                    if self.on_final:
                        self.on_final(voice_text_str, self.full_text)
                elif self.on_result:
                    self.on_result(voice_text_str, False)
        except:
            pass


def main():
    """命令行测试 - 实时麦克风识别"""
    import sys
    
    print("=" * 50)
    print("腾讯云实时语音识别 (中英文混合)")
    print("=" * 50)
    
    def on_result(text, is_final):
        print(f"\r[识别中] {text}", end="", flush=True)
    
    def on_final(sentence, full_text):
        print(f"\n[完成] {sentence}")
    
    asr = RealtimeASR(engine="16k_zh_en")
    
    # 如果有文件参数，识别文件
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        print(f"识别文件: {audio_file}")
        result = asr.recognize_file(audio_file, on_result, on_final)
        print(f"\n完整结果: {result}")
    else:
        # 否则实时麦克风识别
        print("开始实时识别，说话后会实时显示文字")
        print("按 Ctrl+C 停止\n")
        try:
            asr.start(on_result, on_final)
        except KeyboardInterrupt:
            asr.stop()
            print(f"\n\n完整识别结果: {asr.full_text}")


if __name__ == "__main__":
    main()
