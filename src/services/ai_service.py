"""
AI 服务
统一管理 AI 对话、上下文历史
"""

import time
from datetime import datetime
import os
import re
from typing import Generator, Optional, List, Dict, Any
from openai import OpenAI
from openai import APIError, APIConnectionError, APITimeoutError, RateLimitError, AuthenticationError

from ..config import get_config
from ..utils.logger import get_ai_logger
from ..exceptions import (
    AIError, 
    AIConnectionError, 
    AITimeoutError, 
    AIRateLimitError, 
    AIInvalidKeyError
)
from .session_store import get_session_store

logger = get_ai_logger()


class AIService:
    """
    AI 对话服务
    
    提供 AI 问答功能，支持流式和非流式响应，自动管理会话历史。
    
    Attributes:
        client: OpenAI 客户端实例
        model: 使用的 AI 模型名称
        max_history: 保留的最大历史对话轮数
        timeout: 非流式请求超时时间（秒）
        stream_timeout: 流式请求超时时间（秒）
        max_retries: 最大重试次数
        retry_delay: 重试延迟时间（秒）
    
    Example:
        >>> service = get_ai_service()
        >>> answer = service.ask("你好", session_id="user123")
        >>> print(answer)
    """
    
    def __init__(self) -> None:
        config = get_config()
        self._enabled = bool(config.ai.api_base and config.ai.api_key)

        self.client = (
            OpenAI(
                base_url=config.ai.api_base,
                api_key=config.ai.api_key,
            )
            if self._enabled
            else None
        )
        self.model = config.ai.model
        self.max_history = config.ai.max_history
        self.timeout = config.ai.timeout
        self.stream_timeout = config.ai.stream_timeout
        self.max_retries = config.ai.max_retries
        self.retry_delay = config.ai.retry_delay

        if self._enabled:
            env_fallbacks = os.environ.get("AI_MODEL_FALLBACKS") or os.environ.get("GEMINI_MODEL_FALLBACKS")
            logger.info(
                f"[AI] model config | configured={self.model} | env_fallbacks={'set' if (env_fallbacks and env_fallbacks.strip()) else 'unset'}"
            )
            # 跳过模型探测，直接使用配置的模型（节省10秒启动时间）
            # self.model = self._select_working_model(self.model)
            logger.info(f"[AI] 使用配置模型 | model={self.model}")
        
        # 使用会话存储（支持内存/Redis）
        self._session_store = get_session_store()

    @staticmethod
    def _normalize_model_name(model: str) -> str:
        model = (model or "").strip()
        # 支持形如 [y1]gemini-2.5-flash-2 这种标记
        model = re.sub(r"^\[[^\]]+\]", "", model).strip()
        return model

    def _get_model_candidates(self, configured_model: str) -> List[str]:
        raw = (
            os.environ.get("AI_MODEL_FALLBACKS")
            or os.environ.get("GEMINI_MODEL_FALLBACKS")
            or ""
        )

        if raw.strip():
            items = [self._normalize_model_name(x) for x in raw.split(",")]
            candidates = [x for x in items if x]
        else:
            # 默认候选
            candidates = [
                "deepseek-r1-search",
                "gemini-2.5-flash-2",
                "deepseek-v3",
                "gemini-2.5-pro-aistudio-8",
            ]

        configured = self._normalize_model_name(configured_model)
        # 关键：无论默认列表/环境变量顺序如何，都优先尝试配置的默认模型
        if configured:
            candidates = [configured] + [x for x in candidates if x and x != configured]
        # 去重并保持顺序
        seen = set()
        ordered: List[str] = []
        for x in candidates:
            if x and x not in seen:
                seen.add(x)
                ordered.append(x)
        return ordered

    def _probe_model(self, model: str) -> bool:
        """轻量探针：验证模型是否可用。失败不抛出（认证错误除外）。"""
        try:
            # 尽量减少成本/延迟
            self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                stream=False,
                timeout=min(8, int(self.timeout) if self.timeout else 8),
                max_tokens=1,
            )
            return True
        except AuthenticationError:
            # 密钥不对时继续重试其它模型没有意义
            raise
        except Exception:
            return False

    def _select_working_model(self, configured_model: str) -> str:
        candidates = self._get_model_candidates(configured_model)
        # 保底：至少尝试 configured_model
        configured_norm = self._normalize_model_name(configured_model)
        if configured_norm and configured_norm not in candidates:
            candidates.insert(0, configured_norm)

        for m in candidates:
            if not m:
                continue
            try:
                ok = self._probe_model(m)
            except AuthenticationError as e:
                logger.error(f"[AI] 模型探测认证失败 | model={m} | error={e}")
                return configured_norm or m
            if ok:
                if m != configured_norm:
                    logger.warning(f"[AI] 自动切换模型 | from={configured_norm or 'unset'} | to={m}")
                else:
                    logger.info(f"[AI] 模型可用 | model={m}")
                return m

        logger.warning(f"[AI] 所有候选模型探测失败，保留当前配置 | model={configured_norm}")
        return configured_norm
    
    def get_system_prompt(self, short: bool = False) -> str:
        """
        获取带时间上下文的系统提示词
        
        生成包含当前日期、时间、星期等上下文信息的系统提示词，
        指导 AI 使用与用户相同的语言回复。
        
        Args:
            short: 是否使用简短版本（用于简洁回复场景）
        
        Returns:
            系统提示词字符串
        
        Note:
            - 自动检测当前时间并生成时间段（上午/下午/晚上等）
            - 支持中英日多语言回复指导
            - 简短版本限制回复在100字以内
        """
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
            return f"""You are a helpful voice assistant.

{context}

IMPORTANT RULES:
1. Reply in the SAME language as the user's question.
2. Keep answers concise (under 100 words).
3. DO NOT use any markdown formatting (no *, #, -, ```, etc).
4. Use plain text only, suitable for text-to-speech.
5. Use natural spoken language, not written style."""
        
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

    def _get_messages(self, session_id: str, question: str, short: bool = False) -> List[Dict[str, str]]:
        """
        构建完整的消息列表
        
        将系统提示词、历史对话和当前问题组合成完整的消息列表。
        
        Args:
            session_id: 会话ID，用于获取历史记录
            question: 用户当前问题
            short: 是否使用简短系统提示词
        
        Returns:
            消息列表，格式为 [{"role": "system/user/assistant", "content": "..."}]
        """
        history = self._session_store.get(session_id) or []
        
        messages = [{'role': 'system', 'content': self.get_system_prompt(short)}]
        messages.extend(history)
        messages.append({'role': 'user', 'content': question})
        
        return messages
    
    def _save_history(self, session_id: str, question: str, answer: str) -> None:
        """
        保存对话历史到会话存储
        
        将用户问题和 AI 回答保存到会话存储中，自动限制历史记录数量。
        
        Args:
            session_id: 会话ID
            question: 用户问题
            answer: AI 回答
        
        Note:
            - 自动限制历史记录数量为 max_history * 2（问答对）
            - 超出限制时自动删除最旧的记录
        """
        max_messages = self.max_history * 2
        
        # 追加用户消息
        self._session_store.append(
            session_id, 
            {'role': 'user', 'content': question},
            max_messages=max_messages
        )
        # 追加助手消息
        self._session_store.append(
            session_id,
            {'role': 'assistant', 'content': answer},
            max_messages=max_messages
        )
    
    def ask(self, question: str, session_id: str = "default", short: bool = False) -> str:
        """
        AI 问答（非流式）
        
        发送问题到 AI 服务并等待完整回答，自动管理会话历史。
        
        Args:
            question: 用户问题
            session_id: 会话ID，用于区分不同用户或对话，默认为 "default"
            short: 是否使用简短回复模式（限制100字以内）
        
        Returns:
            AI 的完整回答文本
        
        Raises:
            AIInvalidKeyError: API 密钥无效
            AIRateLimitError: 请求速率超限
            AITimeoutError: 请求超时
            AIConnectionError: 网络连接失败
            AIError: 其他 AI 服务错误
        
        Example:
            >>> service = get_ai_service()
            >>> answer = service.ask("今天天气怎么样？", session_id="user123")
            >>> print(answer)
        
        Note:
            - 自动重试最多 max_retries 次
            - 超时时间为 timeout 秒（默认30秒）
            - 自动保存对话历史
        """
        start_time = time.time()
        logger.info(f"[AI] 问答请求 | session={session_id} | question_length={len(question)}")

        if not self._enabled:
            answer = "AI 服务未配置，暂时返回兜底回复。"
            self._save_history(session_id, question, answer)
            return answer
        
        try:
            messages = self._get_messages(session_id, question, short)
            
            # 移除不兼容的参数
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                timeout=self.timeout
            )
            
            answer = response.choices[0].message.content
            self._save_history(session_id, question, answer)
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"[AI] 回答成功 | answer_length={len(answer)} | duration={duration:.2f}ms")
            return answer
            
        except AuthenticationError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[AI] 认证失败 | error={e} | duration={duration:.2f}ms")
            raise AIInvalidKeyError(f"AI服务密钥无效: {e}")
            
        except RateLimitError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[AI] 速率限制 | error={e} | duration={duration:.2f}ms")
            raise AIRateLimitError(f"AI服务请求过于频繁: {e}")
            
        except APITimeoutError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[AI] 请求超时 | error={e} | duration={duration:.2f}ms")
            raise AITimeoutError(f"AI服务请求超时: {e}")
            
        except APIConnectionError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[AI] 连接失败 | error={e} | duration={duration:.2f}ms")
            raise AIConnectionError(f"AI服务连接失败: {e}")
            
        except APIError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[AI] API错误 | error={e} | duration={duration:.2f}ms")
            raise AIError(f"AI服务API错误: {e}")
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[AI] 未知错误 | error={e} | duration={duration:.2f}ms", exc_info=True)
            raise AIError(f"AI服务调用失败: {e}")
    
    def ask_stream(self, question: str, session_id: str = "default") -> Generator[str, None, None]:
        """
        AI 流式问答
        
        发送问题到 AI 服务并以流式方式接收回答，适用于需要实时显示的场景。
        
        Args:
            question: 用户问题
            session_id: 会话ID，用于区分不同用户或对话，默认为 "default"
        
        Yields:
            AI 回答的文本片段，按顺序生成
        
        Raises:
            AIInvalidKeyError: API 密钥无效
            AIRateLimitError: 请求速率超限
            AITimeoutError: 请求超时
            AIConnectionError: 网络连接失败
            AIError: 其他 AI 服务错误
        
        Example:
            >>> service = get_ai_service()
            >>> for chunk in service.ask_stream("讲个故事", session_id="user123"):
            ...     print(chunk, end='', flush=True)
        
        Note:
            - 超时时间为 stream_timeout 秒（默认60秒）
            - 完成后自动保存完整对话历史
            - 适用于 SSE (Server-Sent Events) 等实时场景
        """
        start_time = time.time()
        logger.info(f"[AI] 流式问答 | session={session_id} | question_length={len(question)}")

        if not self._enabled:
            answer = "AI 服务未配置，暂时返回兜底回复。"
            self._save_history(session_id, question, answer)
            yield answer
            return
        
        messages = self._get_messages(session_id, question)
        full_answer = []
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                timeout=self.stream_timeout
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
                duration = (time.time() - start_time) * 1000
                logger.info(f"[AI] 流式回答完成 | length={len(answer_text)} | duration={duration:.2f}ms")
                
        except AuthenticationError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[AI] 流式认证失败 | error={e} | duration={duration:.2f}ms")
            raise AIInvalidKeyError(f"AI服务密钥无效: {e}")
            
        except RateLimitError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[AI] 流式速率限制 | error={e} | duration={duration:.2f}ms")
            raise AIRateLimitError(f"AI服务请求过于频繁: {e}")
            
        except APITimeoutError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[AI] 流式请求超时 | error={e} | duration={duration:.2f}ms")
            raise AITimeoutError(f"AI服务请求超时: {e}")
            
        except APIConnectionError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[AI] 流式连接失败 | error={e} | duration={duration:.2f}ms")
            raise AIConnectionError(f"AI服务连接失败: {e}")
            
        except APIError as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[AI] 流式API错误 | error={e} | duration={duration:.2f}ms")
            raise AIError(f"AI服务API错误: {e}")
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[AI] 流式未知错误 | error={e} | duration={duration:.2f}ms", exc_info=True)
            raise AIError(f"AI服务调用失败: {e}")
    
    def clear_history(self, session_id: str) -> None:
        """
        清除指定会话的历史记录
        
        删除指定会话ID的所有历史对话记录。
        
        Args:
            session_id: 要清除的会话ID
        
        Example:
            >>> service = get_ai_service()
            >>> service.clear_history("user123")
        """
        self._session_store.delete(session_id)
        logger.info(f"[AI] 清除历史 | session={session_id}")


# 全局实例
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """
    获取 AI 服务的全局单例实例
    
    使用单例模式确保整个应用只有一个 AI 服务实例，
    避免重复初始化和资源浪费。
    
    Returns:
        AIService 实例
    
    Example:
        >>> service = get_ai_service()
        >>> answer = service.ask("你好")
    """
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
