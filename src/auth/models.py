"""
认证相关数据模型
使用 SQLite 存储，轻量级方案
"""

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

# 数据库路径
DB_PATH = os.environ.get('AUTH_DB_PATH', 'data/auth.db')


@dataclass
class User:
    """用户"""
    id: int
    username: str
    email: str
    created_at: datetime
    is_active: bool = True
    
    # 配额设置
    daily_requests: int = 1000      # 每日请求数
    daily_tokens: int = 100000      # 每日 Token 数
    daily_audio_seconds: int = 600  # 每日音频秒数 (10分钟)


@dataclass
class ApiKey:
    """API Key"""
    id: int
    user_id: int
    key: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    # 权限
    permissions: str = "all"  # all, stt, tts, ai


@dataclass
class UsageRecord:
    """用量记录"""
    id: int
    user_id: int
    api_key_id: int
    endpoint: str
    request_count: int = 1
    tokens_used: int = 0
    audio_seconds: float = 0
    created_at: datetime = None


class Database:
    """数据库管理"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            conn.executescript('''
                -- 用户表
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    daily_requests INTEGER DEFAULT 1000,
                    daily_tokens INTEGER DEFAULT 100000,
                    daily_audio_seconds INTEGER DEFAULT 600
                );
                
                -- API Key 表
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    key TEXT UNIQUE NOT NULL,
                    name TEXT DEFAULT 'default',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    permissions TEXT DEFAULT 'all',
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                
                -- 用量记录表
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    api_key_id INTEGER NOT NULL,
                    endpoint TEXT NOT NULL,
                    request_count INTEGER DEFAULT 1,
                    tokens_used INTEGER DEFAULT 0,
                    audio_seconds REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (api_key_id) REFERENCES api_keys(id)
                );
                
                -- 每日用量汇总表
                CREATE TABLE IF NOT EXISTS daily_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    total_requests INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    total_audio_seconds REAL DEFAULT 0,
                    UNIQUE(user_id, date),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                
                -- 索引
                CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(key);
                CREATE INDEX IF NOT EXISTS idx_usage_records_user_date ON usage_records(user_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_daily_usage_user_date ON daily_usage(user_id, date);
            ''')
    
    # ==================== 用户操作 ====================
    
    def create_user(self, username: str, email: str, **kwargs) -> int:
        """创建用户"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''INSERT INTO users (username, email, daily_requests, daily_tokens, daily_audio_seconds)
                   VALUES (?, ?, ?, ?, ?)''',
                (username, email, 
                 kwargs.get('daily_requests', 1000),
                 kwargs.get('daily_tokens', 100000),
                 kwargs.get('daily_audio_seconds', 600))
            )
            return cursor.lastrowid
    
    def get_user(self, user_id: int) -> Optional[User]:
        """获取用户"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM users WHERE id = ?', (user_id,)
            ).fetchone()
            if row:
                return User(**dict(row))
        return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM users WHERE username = ?', (username,)
            ).fetchone()
            if row:
                return User(**dict(row))
        return None
    
    # ==================== API Key 操作 ====================
    
    def create_api_key(self, user_id: int, key: str, name: str = 'default', 
                       permissions: str = 'all', expires_at: datetime = None) -> int:
        """创建 API Key"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''INSERT INTO api_keys (user_id, key, name, permissions, expires_at)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, key, name, permissions, expires_at)
            )
            return cursor.lastrowid
    
    def get_api_key(self, key: str) -> Optional[ApiKey]:
        """获取 API Key"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM api_keys WHERE key = ? AND is_active = 1', (key,)
            ).fetchone()
            if row:
                return ApiKey(**dict(row))
        return None
    
    def get_user_api_keys(self, user_id: int) -> List[ApiKey]:
        """获取用户的所有 API Key"""
        with self.get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM api_keys WHERE user_id = ?', (user_id,)
            ).fetchall()
            return [ApiKey(**dict(row)) for row in rows]
    
    def revoke_api_key(self, key: str) -> bool:
        """撤销 API Key"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'UPDATE api_keys SET is_active = 0 WHERE key = ?', (key,)
            )
            return cursor.rowcount > 0
    
    # ==================== 用量操作 ====================
    
    def record_usage(self, user_id: int, api_key_id: int, endpoint: str,
                     tokens: int = 0, audio_seconds: float = 0):
        """记录用量"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            # 记录详细用量
            conn.execute(
                '''INSERT INTO usage_records (user_id, api_key_id, endpoint, tokens_used, audio_seconds)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, api_key_id, endpoint, tokens, audio_seconds)
            )
            
            # 更新每日汇总
            conn.execute(
                '''INSERT INTO daily_usage (user_id, date, total_requests, total_tokens, total_audio_seconds)
                   VALUES (?, ?, 1, ?, ?)
                   ON CONFLICT(user_id, date) DO UPDATE SET
                   total_requests = total_requests + 1,
                   total_tokens = total_tokens + ?,
                   total_audio_seconds = total_audio_seconds + ?''',
                (user_id, today, tokens, audio_seconds, tokens, audio_seconds)
            )
    
    def get_daily_usage(self, user_id: int, date: str = None) -> dict:
        """获取每日用量"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM daily_usage WHERE user_id = ? AND date = ?',
                (user_id, date)
            ).fetchone()
            
            if row:
                return dict(row)
            return {
                'total_requests': 0,
                'total_tokens': 0,
                'total_audio_seconds': 0,
            }


# 全局数据库实例
_db: Optional[Database] = None


def get_db() -> Database:
    """获取数据库实例"""
    global _db
    if _db is None:
        _db = Database()
    return _db
