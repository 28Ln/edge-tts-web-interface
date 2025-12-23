"""
Repository 基类
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List
from contextlib import contextmanager
import sqlite3
import os

T = TypeVar('T')

# 数据库路径
DB_PATH = os.environ.get('AUTH_DB_PATH', 'data/auth.db')


class BaseRepository(ABC, Generic[T]):
    """Repository 基类"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
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
    
    @abstractmethod
    def get_by_id(self, id: int) -> Optional[T]:
        """根据ID获取"""
        pass
    
    @abstractmethod
    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """获取所有记录"""
        pass
    
    @abstractmethod
    def create(self, entity: T) -> int:
        """创建记录"""
        pass
    
    @abstractmethod
    def update(self, entity: T) -> bool:
        """更新记录"""
        pass
    
    @abstractmethod
    def delete(self, id: int) -> bool:
        """删除记录"""
        pass
