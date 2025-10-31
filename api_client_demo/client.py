import requests
import os
import sys

# 服务器的基本 URL
BASE_URL = "http://127.0.0.1:2024"
TTS_URL = f"{BASE_URL}/api/tts"
ASK_AI_URL = f"{BASE_URL}/api/ask_ai"

def generate_audio_question(text, filename="ai_question.wav"):
    """使用 TTS API 生成一个提问的音频文件"""
    print(f"--- 1. 使用 TTS 生成问题音频: '{text}' ---")
    payload = {
        "text": text,
        "file_name": os.path.splitext(filename)[0],
        "output_format": "wav"
    }
    try:
        response = requests.post(TTS_URL, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if data.get("result") == "success":
            file_url = data.get("file_url")
            print(f"TTS 成功，音频文件 URL: {file_url}")
            
            audio_response = requests.get(file_url)
            audio_response.raise_for_status()
            
            with open(filename, 'wb') as f:
                f.write(audio_response.content)
            print(f"问题音频已保存为: {filename}")
            return filename
        else:
            print(f"TTS 失败: {data.get('message')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"请求 TTS API 时出错: {e}")
        return None

def ask_ai_with_audio(audio_file_path):
    """使用音频文件调用新的 AI 问答 API"""
    if not audio_file_path:
        print("没有可用的音频文件，跳过 AI 问答测试。")
        return

    print(f"\n--- 2. 上传音频 '{audio_file_path}' 到 AI 问答 API ---")
    try:
        with open(audio_file_path, 'rb') as f:
            files = {'audio_file': (os.path.basename(audio_file_path), f, 'audio/wav')}
            # 使用 stream=True 来接收流式响应
            response = requests.post(ASK_AI_URL, files=files, stream=True)
            response.raise_for_status()

            print("\n--- 3. AI 模型回复 ---")
            full_response = ""
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                print(chunk, end='', flush=True)
                full_response += chunk
            print("\n--------------------")
            return full_response

    except requests.exceptions.RequestException as e:
        print(f"请求 AI 问答 API 时出错: {e}")
    except FileNotFoundError:
        print(f"错误：找不到音频文件 {audio_file_path}")

def cleanup(file_path):
    """清理下载的临时文件"""
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
        print(f"\n已清理临时文件: {file_path}")

if __name__ == "__main__":
    # 要问 AI 的问题
    question_text = "你好，请用中文介绍一下自己是谁"
    audio_file = None
    
    try:
        # 1. 生成提问的音频文件
        audio_file = generate_audio_question(question_text)
        
        # 2. 使用生成的音频文件去问 AI
        if audio_file:
            ask_ai_with_audio(audio_file)
        
    finally:
        # 3. 清理操作
        cleanup(audio_file)
        print("\n--- AI 问答流程测试完成 ---")