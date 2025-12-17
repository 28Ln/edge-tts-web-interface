#!/usr/bin/env python3
"""
DeepSeek AI 测试脚本
测试多语言回复和对话上下文
"""

import requests

SERVER = "http://127.0.0.1:3003"

def test_ai_stream(question, session="default"):
    """测试流式 AI 问答"""
    print(f"\n问题: {question}")
    print("回答: ", end="", flush=True)
    
    try:
        r = requests.post(
            f"{SERVER}/mcu/ask_stream?session={session}",
            data=question.encode('utf-8'),
            headers={"Content-Type": "text/plain; charset=utf-8"},
            stream=True
        )
        
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                elif data.startswith("[ERROR]"):
                    print(f"\n错误: {data}")
                    break
                else:
                    print(data, end="", flush=True)
        print("\n")
        return True
    except Exception as e:
        print(f"\n请求失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("DeepSeek AI 测试 - 多语言 + 上下文")
    print("=" * 60)
    
    # 测试1: 多语言回复
    print("\n【测试1: 多语言回复】")
    test_ai_stream("今天深圳的天气怎么样？", session="test1")
    test_ai_stream("What is 1+1?", session="test2")
    test_ai_stream("こんにちは", session="test3")
    
    # 测试2: 对话上下文
    print("\n【测试2: 对话上下文】")
    test_ai_stream("我叫小明", session="context_test")
    test_ai_stream("我刚才说我叫什么名字？", session="context_test")
    
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)
