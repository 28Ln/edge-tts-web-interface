"""
配额和用量 Repository
"""

from typing import Optional, List, Dict
from datetime import datetime
from dataclasses import dataclass

from .base import BaseRepository


@dataclass
class UsageRecordEntity:
    """用量记录实体"""
    id: int = None
    user_id: int = None
    api_key_id: int = None
    endpoint: str = ""
    request_count: int = 1
    tokens_used: int = 0
    audio_seconds: float = 0
    created_at: datetime = None


@dataclass
class DailyUsageEntity:
    """每日用量实体"""
    id: int = None
    user_id: int = None
    date: str = ""
    total_requests: int = 0
    total_tokens: int = 0
    total_audio_seconds: float = 0


class QuotaRepository(BaseRepository[UsageRecordEntity]):
    """配额和用量数据访问"""
    
    def get_by_id(self, id: int) -> Optional[UsageRecordEntity]:
        """根据ID获取用量记录"""
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM usage_records WHERE id = ?', (id,)
            ).fetchone()
            if row:
                return self._row_to_entity(row)
        return None
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[UsageRecordEntity]:
        """获取所有用量记录"""
        with self.get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM usage_records ORDER BY created_at DESC LIMIT ? OFFSET ?',
                (limit, offset)
            ).fetchall()
            return [self._row_to_entity(row) for row in rows]
    
    def get_by_user(self, user_id: int, limit: int = 100) -> List[UsageRecordEntity]:
        """获取用户的用量记录"""
        with self.get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM usage_records WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
                (user_id, limit)
            ).fetchall()
            return [self._row_to_entity(row) for row in rows]
    
    def create(self, entity: UsageRecordEntity) -> int:
        """创建用量记录"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''INSERT INTO usage_records (user_id, api_key_id, endpoint, request_count, tokens_used, audio_seconds)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (entity.user_id, entity.api_key_id, entity.endpoint,
                 entity.request_count, entity.tokens_used, entity.audio_seconds)
            )
            return cursor.lastrowid
    
    def update(self, entity: UsageRecordEntity) -> bool:
        """更新用量记录（通常不需要）"""
        return False
    
    def delete(self, id: int) -> bool:
        """删除用量记录"""
        with self.get_connection() as conn:
            cursor = conn.execute('DELETE FROM usage_records WHERE id = ?', (id,))
            return cursor.rowcount > 0
    
    # ==================== 每日用量 ====================
    
    def get_daily_usage(self, user_id: int, date: str = None) -> Optional[DailyUsageEntity]:
        """获取每日用量"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM daily_usage WHERE user_id = ? AND date = ?',
                (user_id, date)
            ).fetchone()
            if row:
                return DailyUsageEntity(
                    id=row['id'],
                    user_id=row['user_id'],
                    date=row['date'],
                    total_requests=row['total_requests'],
                    total_tokens=row['total_tokens'],
                    total_audio_seconds=row['total_audio_seconds']
                )
        return None
    
    def get_daily_usage_range(self, user_id: int, start_date: str, end_date: str) -> List[DailyUsageEntity]:
        """获取日期范围内的用量"""
        with self.get_connection() as conn:
            rows = conn.execute(
                '''SELECT * FROM daily_usage 
                   WHERE user_id = ? AND date >= ? AND date <= ?
                   ORDER BY date''',
                (user_id, start_date, end_date)
            ).fetchall()
            return [DailyUsageEntity(
                id=row['id'],
                user_id=row['user_id'],
                date=row['date'],
                total_requests=row['total_requests'],
                total_tokens=row['total_tokens'],
                total_audio_seconds=row['total_audio_seconds']
            ) for row in rows]
    
    def record_usage(self, user_id: int, api_key_id: int, endpoint: str,
                     tokens: int = 0, audio_seconds: float = 0) -> None:
        """记录用量（同时更新详细记录和每日汇总）"""
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
    
    # ==================== 统计 ====================
    
    def get_user_stats(self, user_id: int) -> Dict:
        """获取用户统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        daily = self.get_daily_usage(user_id, today)
        
        return {
            'today_requests': daily.total_requests if daily else 0,
            'today_tokens': daily.total_tokens if daily else 0,
            'today_audio_seconds': daily.total_audio_seconds if daily else 0,
        }
    
    def get_global_stats(self) -> Dict:
        """获取全局统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            # 今日总量
            row = conn.execute(
                '''SELECT SUM(total_requests) as requests, 
                          SUM(total_tokens) as tokens,
                          SUM(total_audio_seconds) as audio
                   FROM daily_usage WHERE date = ?''',
                (today,)
            ).fetchone()
            
            return {
                'today_requests': row['requests'] or 0 if row else 0,
                'today_tokens': row['tokens'] or 0 if row else 0,
                'today_audio_seconds': row['audio'] or 0 if row else 0,
            }
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """清理旧记录"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''DELETE FROM usage_records 
                   WHERE created_at < datetime('now', ?)''',
                (f'-{days} days',)
            )
            return cursor.rowcount
    
    def _row_to_entity(self, row) -> UsageRecordEntity:
        """行数据转实体"""
        return UsageRecordEntity(
            id=row['id'],
            user_id=row['user_id'],
            api_key_id=row['api_key_id'],
            endpoint=row['endpoint'],
            request_count=row['request_count'],
            tokens_used=row['tokens_used'],
            audio_seconds=row['audio_seconds'],
            created_at=row['created_at']
        )
