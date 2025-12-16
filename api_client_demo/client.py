import requests
import os
import json

# 服务器的基本 URL (支持环境变量配置)
import os
BASE_URL = os.environ.get('SERVER_URL', 'http://127.0.0.1:3003')
TTS_URL = f"{BASE_URL}/api/tts"
ASK_AI_URL = f"{BASE_URL}/api/ask_ai"

def generate_audio_question(text, filename="ai_question.wav"):
    """使用 TTS API 生成一个提问的音频文件"""
    print(f"--- 步骤 1: 开始使用 TTS API 生成问题音频 ---")
    print(f"请求文本: '{text}'")
    payload = {
        "text": text,
        "file_name": os.path.splitext(filename)[0],
        "output_format": "wav"
    }
    try:
        print(f"发送 POST 请求到: {TTS_URL}")
        response = requests.post(TTS_URL, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if data.get("result") == "success":
            file_url = data.get("file_url")
            print(f"TTS API 响应成功。音频文件 URL: {file_url}")
            
            print(f"正在从 {file_url} 下载音频文件...")
            audio_response = requests.get(file_url)
            audio_response.raise_for_status()
            
            with open(filename, 'wb') as f:
                f.write(audio_response.content)
            print(f"音频文件已成功保存为: {filename}")
            return filename
        else:
            print(f"TTS API 返回错误: {data.get('message')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"请求 TTS API 时发生网络错误: {e}")
        return None

def ask_ai_with_audio(audio_file_path):
    """使用音频文件调用新的 AI 问答 API 并解析 multipart 响应"""
    if not audio_file_path:
        print("错误: 未提供音频文件路径，无法进行 AI 问答。")
        return

    print(f"\n--- 步骤 2: 开始使用 STT 和 AI 问答 API ---")
    print(f"准备上传音频文件: '{audio_file_path}'")
    try:
        with open(audio_file_path, 'rb') as f:
            files = {'audio_file': (os.path.basename(audio_file_path), f, 'audio/wav')}
            print(f"发送 POST 请求到: {ASK_AI_URL}")
            response = requests.post(ASK_AI_URL, files=files, stream=True)
            response.raise_for_status()

            print("\n--- 步骤 3: 解析服务器响应 ---")
            
            content_type = response.headers.get('content-type')
            if 'multipart/x-mixed-replace' not in content_type:
                print(f"错误: 期望的响应类型是 'multipart/x-mixed-replace'，但收到了 '{content_type}'")
                print(f"原始响应: {response.text}")
                return

            boundary = content_type.split('boundary=')[1]
            
            stt_printed = False
            ai_response_started = False

            for part in response.iter_content(chunk_size=None):
                # 注意：这是一个简化的解析器，适用于本示例
                if part.startswith(b'--' + boundary.encode()):
                    headers, body = part.split(b'\r\n\r\n', 1)
                    if b'application/json' in headers:
                        stt_data = json.loads(body.strip())
                        print(f"语音识别 (STT) 结果: '{stt_data.get('transcription')}'")
                        stt_printed = True
                    elif b'text/plain' in headers:
                        if not ai_response_started:
                            print("\n--- AI 模型回复 ---")
                            ai_response_started = True
                        print(body.decode('utf-8'), end='', flush=True)

            if not stt_printed:
                print("警告: 未能从响应中解析出 STT 结果。")
            
            print("\n--------------------")

    except requests.exceptions.RequestException as e:
        print(f"请求 AI 问答 API 时发生网络错误: {e}")
    except FileNotFoundError:
        print(f"错误：无法找到要上传的音频文件 {audio_file_path}")
    except Exception as e:
        print(f"处理响应时发生未知错误: {e}")


def cleanup(file_path):
    """清理下载的临时文件"""
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
        print(f"\n--- 清理工作: 已删除临时文件 '{file_path}' ---")

if __name__ == "__main__":
    question_text = "你好，请用中文介绍一下你自己是谁"
    audio_file = None
    
    print("========================================")
    print("=      开始执行语音 AI 问答流程      =")
    print("========================================")
    
    try:
        audio_file = generate_audio_question(question_text)
        if audio_file:
            ask_ai_with_audio(audio_file)
        else:
            print("\n由于未能生成音频文件，无法继续执行 AI 问答流程。")
        
    finally:
        cleanup(audio_file)
        print("\n========================================")
        print("=      流程执行完毕      =")
        print("========================================")