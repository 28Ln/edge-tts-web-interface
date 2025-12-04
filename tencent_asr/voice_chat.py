# 语音对话：语音转文字 + AI 对话
import os
import sys
from openai import OpenAI

from asr_client import TencentASR
from config import AI_BASE_URL, AI_API_KEY, AI_MODEL


class VoiceChat:
    """语音对话助手：语音 → 文字 → AI 回复"""
    
    def __init__(self):
        self.asr = TencentASR()
        self.ai_client = OpenAI(base_url=AI_BASE_URL, api_key=AI_API_KEY)
        self.conversation_history = []
    
    def speech_to_text(self, audio_path: str) -> str:
        """语音转文字"""
        # 根据文件扩展名确定格式
        ext = os.path.splitext(audio_path)[1].lower().lstrip(".")
        if ext in ["wav", "mp3", "m4a", "flac", "ogg", "amr"]:
            voice_format = ext
        else:
            voice_format = "wav"
        
        result = self.asr.recognize(audio_path, voice_format)
        
        if result["success"]:
            return result["text"]
        else:
            raise Exception(f"语音识别失败: {result['error']}")
    
    def chat(self, user_message: str, stream: bool = True):
        """
        与 AI 对话
        
        Args:
            user_message: 用户消息
            stream: 是否流式输出
        
        Returns:
            如果 stream=True，返回生成器；否则返回完整回复
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        messages = [
            {"role": "system", "content": "你是一个友好的AI助手，请用简洁清晰的中文回答问题。"},
            *self.conversation_history
        ]
        
        if stream:
            return self._stream_chat(messages)
        else:
            return self._sync_chat(messages)
    
    def _stream_chat(self, messages):
        """流式对话"""
        response = self.ai_client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            stream=True
        )
        
        full_response = ""
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                full_response += content
                yield content
        
        # 保存 AI 回复到历史
        self.conversation_history.append({
            "role": "assistant",
            "content": full_response
        })

    def _sync_chat(self, messages) -> str:
        """同步对话"""
        response = self.ai_client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            stream=False
        )
        
        reply = response.choices[0].message.content
        self.conversation_history.append({
            "role": "assistant",
            "content": reply
        })
        return reply
    
    def voice_chat(self, audio_path: str, stream: bool = True):
        """
        完整的语音对话流程
        
        Args:
            audio_path: 音频文件路径
            stream: 是否流式输出 AI 回复
        
        Returns:
            dict: {"transcription": str, "reply": str 或 generator}
        """
        # 1. 语音转文字
        transcription = self.speech_to_text(audio_path)
        print(f"[语音识别] {transcription}")
        
        # 2. AI 对话
        reply = self.chat(transcription, stream=stream)
        
        return {
            "transcription": transcription,
            "reply": reply
        }
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []


def main():
    """命令行测试"""
    if len(sys.argv) < 2:
        print("用法: python voice_chat.py <音频文件路径>")
        print("示例: python voice_chat.py test.wav")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    
    if not os.path.exists(audio_path):
        print(f"错误: 文件不存在 - {audio_path}")
        sys.exit(1)
    
    print("=" * 50)
    print("语音对话助手 (腾讯云 ASR + AI)")
    print("=" * 50)
    
    chat = VoiceChat()
    
    try:
        result = chat.voice_chat(audio_path, stream=True)
        
        print(f"\n[AI 回复] ", end="", flush=True)
        for chunk in result["reply"]:
            print(chunk, end="", flush=True)
        print("\n")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
