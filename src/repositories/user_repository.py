"""
用户 Repository
"""

from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass

from .base import BaseRepository


@dataclass
class UserEntity:
    """用户实体"""
    id: int = None
    username: str = ""
    email: str = ""
    created_at: datetime = None
    is_active: bool = True
    daily_requests: int = 1000
    daily_tokens: int = 100000
    daily_audio_seconds: int = 600


class UserRepository(BaseRepository[UserEntity]):
    """用户数据访问"""
    
    def get_by_id(self, id: int) -> Optional[UserEntity]:
        """根据ID获取用户"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM users WHERE id = ?', (id,)
            ).fetchone()
            if row:
                return self._row_to_entity(row)
        return None
    
    def get_by_username(self, username: str) -> Optional[UserEntity]:
        """根据用户名获取用户"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM users WHERE username = ?', (username,)
            ).fetchone()
            if row:
                return self._row_to_entity(row)
        return None
    
    def get_by_email(self, email: str) -> Optional[UserEntity]:
        """根据邮箱获取用户"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM users WHERE email = ?', (email,)
            ).fetchone()
            if row:
                return self._row_to_entity(row)
        return None
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[UserEntity]:
        """获取所有用户"""
        with self.get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?',
                (limit, offset)
            ).fetchall()
            return [self._row_to_entity(row) for row in rows]
    
    def get_active_users(self, limit: int = 100) -> List[UserEntity]:
        """获取活跃用户"""
        with self.get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM users WHERE is_active = 1 ORDER BY created_at DESC LIMIT ?',
                (limit,)
            ).fetchall()
            return [self._row_to_entity(row) for row in rows]
    
    def count(self) -> int:
        """统计用户数量"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()
            return row['count'] if row else 0
    
    def count_active(self) -> int:
        """统计活跃用户数量"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT COUNT(*) as count FROM users WHERE is_active = 1'
            ).fetchone()
            return row['count'] if row else 0
    
    def create(self, entity: UserEntity) -> int:
        """创建用户"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''INSERT INTO users (username, email, is_active, daily_requests, daily_tokens, daily_audio_seconds)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (entity.username, entity.email, entity.is_active,
                 entity.daily_requests, entity.daily_tokens, entity.daily_audio_seconds)
            )
            return cursor.lastrowid
    
    def update(self, entity: UserEntity) -> bool:
        """更新用户"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''UPDATE users SET username = ?, email = ?, is_active = ?,
                   daily_requests = ?, daily_tokens = ?, daily_audio_seconds = ?
                   WHERE id = ?''',
                (entity.username, entity.email, entity.is_active,
                 entity.daily_requests, entity.daily_tokens, entity.daily_audio_seconds,
                 entity.id)
            )
            return cursor.rowcount > 0
    
    def delete(self, id: int) -> bool:
        """删除用户"""
        with self.get_connection() as conn:
            cursor = conn.execute('DELETE FROM users WHERE id = ?', (id,))
            return cursor.rowcount > 0
    
    def toggle_active(self, id: int) -> bool:
        """切换用户状态"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'UPDATE users SET is_active = NOT is_active WHERE id = ?', (id,)
            )
            return cursor.rowcount > 0
    
    def _row_to_entity(self, row) -> UserEntity:
        """行数据转实体"""
        return UserEntity(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            created_at=row['created_at'],
            is_active=bool(row['is_active']),
            daily_requests=row['daily_requests'],
            daily_tokens=row['daily_tokens'],
            daily_audio_seconds=row['daily_audio_seconds']
        )
