"""
AI 服务
统一管理 AI 对话、上下文历史
"""

from datetime import datetime
from typing import Generator, Optional
from openai import OpenAI

from ..config import get_config
from ..utils.logger import get_ai_logger
from ..exceptions import AIError

logger = get_ai_logger()


class AIService:
    """AI 服务"""
    
    def __init__(self):
        config = get_config()
        self.client = OpenAI(
            base_url=config.ai.api_base,
            api_key=config.ai.api_key,
        )
        self.model = config.ai.model
        self.max_history = config.ai.max_history
        
        # 对话历史 {session_id: [messages]}
        self._history = {}
    
    def get_system_prompt(self, short: bool = False) -> str:
        """获取带时间上下文的 system prompt"""
        now = datetime.now()
        
        date_str = now.strftime("%Y年%m月%d日")
        time_str = now.strftime("%H:%M")
        weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday = weekday_map[now.weekday()]
        
        hour = now.hour
        if 5 <= hour < 12:
            period = "上午"
        elif 12 <= hour < 14:
            period = "中午"
        elif 14 <= hour < 18:
            period = "下午"
        elif 18 <= hour < 22:
            period = "晚上"
        else:
            period = "深夜"
        
        context = f"""Current time context:
- Date: {date_str} ({weekday})
- Time: {time_str} ({period})
- Location: China (default)"""

        if short:
            return f"""You are a helpful assistant.

{context}

IMPORTANT: Reply in the SAME language as the user's question.
Keep answers concise (under 100 words)."""
        
        return f"""You are a helpful assistant.

{context}

IMPORTANT RULES:
1. You MUST reply in the SAME language as the user's question.
   - Chinese question → Chinese answer
   - English question → English answer
   - Japanese question → Japanese answer
   
2. When user mentions "今天/today/今日", use the current date above.
   When user mentions "现在/now", use the current time above.
   
3. Keep your answers concise, accurate and helpful.
4. If you don't know something, say so honestly."""

    def _get_messages(self, session_id: str, question: str, short: bool = False) -> list:
        """构建消息列表（含历史）"""
        history = self._history.get(session_id, [])
        
        messages = [{'role': 'system', 'content': self.get_system_prompt(short)}]
        messages.extend(history)
        messages.append({'role': 'user', 'content': question})
        
        return messages
    
    def _save_history(self, session_id: str, question: str, answer: str):
        """保存对话历史"""
        if session_id not in self._history:
            self._history[session_id] = []
        
        history = self._history[session_id]
        history.append({'role': 'user', 'content': question})
        history.append({'role': 'assistant', 'content': answer})
        
        # 只保留最近 N 轮
        max_messages = self.max_history * 2
        if len(history) > max_messages:
            self._history[session_id] = history[-max_messages:]
    
    def ask(self, question: str, session_id: str = "default", short: bool = False) -> str:
        """
        AI 问答（非流式）
        
        Args:
            question: 问题
            session_id: 会话ID
            short: 是否使用简短回复
        
        Returns:
            AI 回答
        """
        logger.info(f"[AI] 问答请求 | session={session_id} | question={question[:50]}...")
        
        try:
            messages = self._get_messages(session_id, question, short)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            
            answer = response.choices[0].message.content
            self._save_history(session_id, question, answer)
            
            logger.info(f"[AI] 回答成功 | answer={answer[:50]}...")
            return answer
            
        except Exception as e:
            logger.error(f"[AI] 调用失败: {e}")
            raise AIError(f"AI服务调用失败: {e}")
    
    def ask_stream(self, question: str, session_id: str = "default") -> Generator[str, None, None]:
        """
        AI 流式问答
        
        Args:
            question: 问题
            session_id: 会话ID
        
        Yields:
            AI 回答片段
        """
        logger.info(f"[AI] 流式问答 | session={session_id} | question={question[:50]}...")
        
        messages = self._get_messages(session_id, question)
        full_answer = []
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        full_answer.append(content)
                        yield content
            
            # 保存历史
            if full_answer:
                answer_text = ''.join(full_answer)
                self._save_history(session_id, question, answer_text)
                logger.info(f"[AI] 流式回答完成 | length={len(answer_text)}")
                
        except Exception as e:
            logger.error(f"[AI] 流式调用失败: {e}")
            raise AIError(f"AI服务调用失败: {e}")
    
    def clear_history(self, session_id: str):
        """清除会话历史"""
        if session_id in self._history:
            del self._history[session_id]
            logger.info(f"[AI] 清除历史 | session={session_id}")


# 全局实例
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """获取 AI 服务实例"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
