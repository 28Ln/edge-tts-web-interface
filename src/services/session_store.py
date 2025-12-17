"""
会话存储
支持内存存储和 Redis 存储
"""

import json
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from ..config import get_config
from ..utils.logger import get_logger

logger = get_logger("session")


class SessionStore(ABC):
    """会话存储抽象基类"""
    
    @abstractmethod
    def get(self, session_id: str) -> Optional[List[Dict]]:
        """获取会话历史"""
        pass
    
    @abstractmethod
    def set(self, session_id: str, messages: List[Dict], ttl: int = 3600):
        """保存会话历史"""
        pass
    
    @abstractmethod
    def delete(self, session_id: str):
        """删除会话"""
        pass
    
    @abstractmethod
    def append(self, session_id: str, message: Dict, max_messages: int = 10):
        """追加消息到会话"""
        pass


class MemorySessionStore(SessionStore):
    """内存会话存储（单机模式）"""
    
    def __init__(self):
        self._store: Dict[str, Dict] = {}
    
    def get(self, session_id: str) -> Optional[List[Dict]]:
        data = self._store.get(session_id)
        if data:
            # 检查过期
            if data.get('expires_at') and datetime.now() > data['expires_at']:
                del self._store[session_id]
                return None
            return data.get('messages', [])
        return None
    
    def set(self, session_id: str, messages: List[Dict], ttl: int = 3600):
        self._store[session_id] = {
            'messages': messages,
            'expires_at': datetime.now() + timedelta(seconds=ttl),
        }
    
    def delete(self, session_id: str):
        self._store.pop(session_id, None)
    
    def append(self, session_id: str, message: Dict, max_messages: int = 10):
        messages = self.get(session_id) or []
        messages.append(message)
        # 保留最近 N 条
        if len(messages) > max_messages:
            messages = messages[-max_messages:]
        self.set(session_id, messages)


class RedisSessionStore(SessionStore):
    """Redis 会话存储（分布式模式）"""
    
    def __init__(self, redis_url: str):
        import redis
        self._redis = redis.from_url(redis_url)
        self._prefix = "session:"
    
    def _key(self, session_id: str) -> str:
        return f"{self._prefix}{session_id}"
    
    def get(self, session_id: str) -> Optional[List[Dict]]:
        data = self._redis.get(self._key(session_id))
        if data:
            return json.loads(data)
        return None
    
    def set(self, session_id: str, messages: List[Dict], ttl: int = 3600):
        self._redis.setex(
            self._key(session_id),
            ttl,
            json.dumps(messages, ensure_ascii=False)
        )
    
    def delete(self, session_id: str):
        self._redis.delete(self._key(session_id))
    
    def append(self, session_id: str, message: Dict, max_messages: int = 10):
        messages = self.get(session_id) or []
        messages.append(message)
        if len(messages) > max_messages:
            messages = messages[-max_messages:]
        self.set(session_id, messages)


# 全局实例
_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """获取会话存储实例"""
    global _session_store
    if _session_store is None:
        config = get_config()
        if config.redis_url:
            logger.info("使用 Redis 会话存储")
            _session_store = RedisSessionStore(config.redis_url)
        else:
            logger.info("使用内存会话存储")
            _session_store = MemorySessionStore()
    return _session_store
