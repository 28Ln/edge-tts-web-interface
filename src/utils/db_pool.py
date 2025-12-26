"""数据库连接池

**Feature: production-readiness**
"""

import os
import time
import sqlite3
from typing import Optional, Dict, Any
from dataclasses import dataclass
from threading import Lock, Condition
from queue import Queue, Empty, Full
from contextlib import contextmanager

from src.utils.logger import get_logger


@dataclass
class PoolConfig:
    """连接池配置"""
    min_connections: int = 2
    max_connections: int = 10
    connection_timeout: float = 30.0  # 获取连接超时（秒）
    idle_timeout: float = 300.0  # 空闲连接超时（秒）
    max_retries: int = 3
    retry_delay: float = 1.0  # 重试延迟（秒）


class PooledConnection:
    """池化连接包装器"""
    
    def __init__(self, connection: sqlite3.Connection, pool: 'ConnectionPool'):
        self._connection = connection
        self._pool = pool
        self._created_at = time.time()
        self._last_used_at = time.time()
        self._in_use = False
    
    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection
    
    @property
    def is_idle_expired(self) -> bool:
        """检查空闲连接是否过期"""
        if self._in_use:
            return False
        return time.time() - self._last_used_at > self._pool.config.idle_timeout
    
    def mark_used(self) -> None:
        """标记为使用中"""
        self._in_use = True
        self._last_used_at = time.time()
    
    def mark_released(self) -> None:
        """标记为已释放"""
        self._in_use = False
        self._last_used_at = time.time()
    
    def close(self) -> None:
        """关闭底层连接"""
        try:
            self._connection.close()
        except Exception:
            pass


class ConnectionPool:
    """SQLite 数据库连接池
    
    实现连接复用、队列等待、指数退避重试
    """
    
    def __init__(self, db_path: str, config: PoolConfig = None):
        self.db_path = db_path
        self.config = config or PoolConfig()
        self.logger = get_logger('db_pool')
        
        self._lock = Lock()
        self._condition = Condition(self._lock)
        
        # 连接池
        self._available: list[PooledConnection] = []
        self._in_use: set[PooledConnection] = set()
        self._total_created = 0
        
        # 统计
        self._stats = {
            'connections_created': 0,
            'connections_reused': 0,
            'connections_closed': 0,
            'wait_count': 0,
            'timeout_count': 0,
            'retry_count': 0
        }
        
        # 初始化最小连接数
        self._initialize_pool()
        
        self.logger.info(
            f"连接池初始化完成: db={db_path}, "
            f"min={self.config.min_connections}, max={self.config.max_connections}"
        )
    
    def _initialize_pool(self) -> None:
        """初始化连接池"""
        for _ in range(self.config.min_connections):
            try:
                conn = self._create_connection()
                if conn:
                    self._available.append(conn)
            except Exception as e:
                self.logger.warning(f"初始化连接失败: {e}")
    
    def _create_connection(self) -> Optional[PooledConnection]:
        """创建新连接"""
        try:
            connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=self.config.connection_timeout
            )
            connection.row_factory = sqlite3.Row
            
            pooled = PooledConnection(connection, self)
            self._total_created += 1
            self._stats['connections_created'] += 1
            
            self.logger.debug(f"创建新连接，当前总数: {self._total_created}")
            return pooled
        except Exception as e:
            self.logger.error(f"创建连接失败: {e}")
            return None
    
    def get_connection(self, timeout: float = None) -> Optional[PooledConnection]:
        """获取连接
        
        Args:
            timeout: 超时时间（秒），None 使用默认配置
            
        Returns:
            PooledConnection 或 None（超时）
        """
        timeout = timeout or self.config.connection_timeout
        deadline = time.time() + timeout
        
        with self._condition:
            while True:
                # 尝试从可用池获取
                if self._available:
                    conn = self._available.pop()
                    
                    # 检查连接是否有效
                    if self._is_connection_valid(conn):
                        conn.mark_used()
                        self._in_use.add(conn)
                        self._stats['connections_reused'] += 1
                        return conn
                    else:
                        # 连接无效，关闭并继续
                        conn.close()
                        self._total_created -= 1
                        self._stats['connections_closed'] += 1
                        continue
                
                # 尝试创建新连接
                current_total = len(self._available) + len(self._in_use)
                if current_total < self.config.max_connections:
                    conn = self._create_connection()
                    if conn:
                        conn.mark_used()
                        self._in_use.add(conn)
                        return conn
                
                # 等待连接释放
                remaining = deadline - time.time()
                if remaining <= 0:
                    self._stats['timeout_count'] += 1
                    self.logger.warning("获取连接超时")
                    return None
                
                self._stats['wait_count'] += 1
                self._condition.wait(timeout=remaining)
    
    def release_connection(self, conn: PooledConnection) -> None:
        """释放连接回池"""
        with self._condition:
            if conn in self._in_use:
                self._in_use.remove(conn)
                conn.mark_released()
                
                # 检查是否需要保留
                current_total = len(self._available) + len(self._in_use)
                if current_total <= self.config.max_connections:
                    self._available.append(conn)
                else:
                    conn.close()
                    self._total_created -= 1
                    self._stats['connections_closed'] += 1
                
                # 通知等待的线程
                self._condition.notify()
    
    def _is_connection_valid(self, conn: PooledConnection) -> bool:
        """检查连接是否有效"""
        try:
            # 检查空闲超时
            if conn.is_idle_expired:
                return False
            
            # 执行简单查询验证连接
            conn.connection.execute("SELECT 1")
            return True
        except Exception:
            return False

    @contextmanager
    def connection(self):
        """上下文管理器获取连接
        
        Usage:
            with pool.connection() as conn:
                cursor = conn.execute("SELECT * FROM users")
        """
        conn = None
        retries = 0
        last_error = None
        
        while retries < self.config.max_retries:
            try:
                conn = self.get_connection()
                if conn:
                    yield conn.connection
                    return
                else:
                    raise ConnectionError("无法获取数据库连接")
            except Exception as e:
                last_error = e
                retries += 1
                self._stats['retry_count'] += 1
                
                if retries < self.config.max_retries:
                    # 指数退避
                    delay = self.config.retry_delay * (2 ** (retries - 1))
                    self.logger.warning(
                        f"连接失败，{delay:.1f}s 后重试 ({retries}/{self.config.max_retries}): {e}"
                    )
                    time.sleep(delay)
            finally:
                if conn:
                    self.release_connection(conn)
        
        raise ConnectionError(f"获取连接失败，已重试 {retries} 次: {last_error}")
    
    def execute_with_retry(self, sql: str, params: tuple = None) -> Any:
        """带重试的 SQL 执行
        
        Args:
            sql: SQL 语句
            params: 参数元组
            
        Returns:
            执行结果
        """
        with self.connection() as conn:
            cursor = conn.execute(sql, params or ())
            conn.commit()
            return cursor
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        with self._lock:
            return {
                'available': len(self._available),
                'in_use': len(self._in_use),
                'total': self._total_created,
                'max': self.config.max_connections,
                **self._stats
            }
    
    def cleanup_idle_connections(self) -> int:
        """清理空闲过期连接
        
        Returns:
            清理的连接数
        """
        with self._lock:
            cleaned = 0
            remaining = []
            
            for conn in self._available:
                if conn.is_idle_expired:
                    conn.close()
                    self._total_created -= 1
                    self._stats['connections_closed'] += 1
                    cleaned += 1
                else:
                    remaining.append(conn)
            
            self._available = remaining
            
            if cleaned > 0:
                self.logger.info(f"清理了 {cleaned} 个空闲连接")
            
            return cleaned
    
    def close_all(self) -> None:
        """关闭所有连接"""
        with self._lock:
            for conn in self._available:
                conn.close()
            for conn in self._in_use:
                conn.close()
            
            self._available.clear()
            self._in_use.clear()
            self._total_created = 0
            
            self.logger.info("连接池已关闭")
    
    @property
    def size(self) -> int:
        """当前连接池大小"""
        with self._lock:
            return len(self._available) + len(self._in_use)
    
    @property
    def available_count(self) -> int:
        """可用连接数"""
        with self._lock:
            return len(self._available)
    
    @property
    def in_use_count(self) -> int:
        """使用中连接数"""
        with self._lock:
            return len(self._in_use)


# 全局连接池实例
_connection_pools: Dict[str, ConnectionPool] = {}
_pools_lock = Lock()


def get_connection_pool(db_path: str = None, config: PoolConfig = None) -> ConnectionPool:
    """获取连接池实例
    
    Args:
        db_path: 数据库路径，默认从环境变量读取
        config: 连接池配置
        
    Returns:
        ConnectionPool 实例
    """
    global _connection_pools
    
    if db_path is None:
        db_path = os.environ.get('DATABASE_PATH', 'data/auth.db')
    
    with _pools_lock:
        if db_path not in _connection_pools:
            _connection_pools[db_path] = ConnectionPool(db_path, config)
        return _connection_pools[db_path]


def close_all_pools() -> None:
    """关闭所有连接池"""
    global _connection_pools
    
    with _pools_lock:
        for pool in _connection_pools.values():
            pool.close_all()
        _connection_pools.clear()
