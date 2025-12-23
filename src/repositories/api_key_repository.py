"""
API Key Repository
"""

from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass

from .base import BaseRepository


@dataclass
class APIKeyEntity:
    """API Key 实体"""
    id: int = None
    user_id: int = None
    key: str = ""
    name: str = "default"
    created_at: datetime = None
    expires_at: datetime = None
    is_active: bool = True
    permissions: str = "all"


class APIKeyRepository(BaseRepository[APIKeyEntity]):
    """API Key 数据访问"""
    
    def get_by_id(self, id: int) -> Optional[APIKeyEntity]:
        """根据ID获取"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM api_keys WHERE id = ?', (id,)
            ).fetchone()
            if row:
                return self._row_to_entity(row)
        return None
    
    def get_by_key(self, key: str) -> Optional[APIKeyEntity]:
        """根据Key获取"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM api_keys WHERE key = ?', (key,)
            ).fetchone()
            if row:
                return self._row_to_entity(row)
        return None
    
    def get_active_by_key(self, key: str) -> Optional[APIKeyEntity]:
        """获取有效的Key"""
        with self.get_connection() as conn:
            row = conn.execute(
                '''SELECT * FROM api_keys 
                   WHERE key = ? AND is_active = 1 
                   AND (expires_at IS NULL OR expires_at > datetime('now'))''',
                (key,)
            ).fetchone()
            if row:
                return self._row_to_entity(row)
        return None
    
    def get_by_user_id(self, user_id: int) -> List[APIKeyEntity]:
        """获取用户的所有Key"""
        with self.get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at DESC',
                (user_id,)
            ).fetchall()
            return [self._row_to_entity(row) for row in rows]
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[APIKeyEntity]:
        """获取所有Key"""
        with self.get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM api_keys ORDER BY created_at DESC LIMIT ? OFFSET ?',
                (limit, offset)
            ).fetchall()
            return [self._row_to_entity(row) for row in rows]
    
    def get_active_keys(self, limit: int = 100) -> List[APIKeyEntity]:
        """获取所有有效Key"""
        with self.get_connection() as conn:
            rows = conn.execute(
                '''SELECT * FROM api_keys WHERE is_active = 1 
                   AND (expires_at IS NULL OR expires_at > datetime('now'))
                   ORDER BY created_at DESC LIMIT ?''',
                (limit,)
            ).fetchall()
            return [self._row_to_entity(row) for row in rows]
    
    def count(self) -> int:
        """统计Key数量"""
        with self.get_connection() as conn:
            row = conn.execute('SELECT COUNT(*) as count FROM api_keys').fetchone()
            return row['count'] if row else 0
    
    def count_active(self) -> int:
        """统计有效Key数量"""
        with self.get_connection() as conn:
            row = conn.execute(
                '''SELECT COUNT(*) as count FROM api_keys 
                   WHERE is_active = 1 AND (expires_at IS NULL OR expires_at > datetime('now'))'''
            ).fetchone()
            return row['count'] if row else 0
    
    def create(self, entity: APIKeyEntity) -> int:
        """创建Key"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''INSERT INTO api_keys (user_id, key, name, expires_at, is_active, permissions)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (entity.user_id, entity.key, entity.name, 
                 entity.expires_at, entity.is_active, entity.permissions)
            )
            return cursor.lastrowid
    
    def update(self, entity: APIKeyEntity) -> bool:
        """更新Key"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''UPDATE api_keys SET name = ?, expires_at = ?, is_active = ?, permissions = ?
                   WHERE id = ?''',
                (entity.name, entity.expires_at, entity.is_active, entity.permissions, entity.id)
            )
            return cursor.rowcount > 0
    
    def delete(self, id: int) -> bool:
        """删除Key"""
        with self.get_connection() as conn:
            cursor = conn.execute('DELETE FROM api_keys WHERE id = ?', (id,))
            return cursor.rowcount > 0
    
    def revoke(self, key: str) -> bool:
        """撤销Key"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'UPDATE api_keys SET is_active = 0 WHERE key = ?', (key,)
            )
            return cursor.rowcount > 0
    
    def revoke_by_user(self, user_id: int) -> int:
        """撤销用户所有Key"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'UPDATE api_keys SET is_active = 0 WHERE user_id = ?', (user_id,)
            )
            return cursor.rowcount
    
    def _row_to_entity(self, row) -> APIKeyEntity:
        """行数据转实体"""
        return APIKeyEntity(
            id=row['id'],
            user_id=row['user_id'],
            key=row['key'],
            name=row['name'],
            created_at=row['created_at'],
            expires_at=row['expires_at'],
            is_active=bool(row['is_active']),
            permissions=row['permissions']
        )
