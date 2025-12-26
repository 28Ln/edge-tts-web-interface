"""数据库连接池测试

**Feature: production-readiness**
"""

import os
import time
import tempfile
import threading
import pytest
from hypothesis import given, strategies as st, settings, assume

from src.utils.db_pool import (
    ConnectionPool, PoolConfig, PooledConnection,
    get_connection_pool, close_all_pools
)


class TestConnectionPool:
    """连接池测试"""
    
    def setup_method(self):
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # 初始化数据库
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()
    
    def teardown_method(self):
        close_all_pools()
        try:
            os.unlink(self.db_path)
        except:
            pass
    
    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=5, deadline=None)
    def test_pool_size_limit(self, max_connections):
        """**Property 7: 连接池大小限制**
        For any configured max_connections value,
        the pool should never exceed that limit
        **Validates: Requirements 6.1**
        """
        config = PoolConfig(min_connections=1, max_connections=max_connections)
        pool = ConnectionPool(self.db_path, config)
        
        try:
            # 获取所有可能的连接
            connections = []
            for _ in range(max_connections + 2):  # 减少尝试次数
                conn = pool.get_connection(timeout=0.05)  # 更短的超时
                if conn:
                    connections.append(conn)
            
            # 验证不超过最大限制
            assert len(connections) <= max_connections
            assert pool.size <= max_connections
        finally:
            for conn in connections:
                pool.release_connection(conn)
            pool.close_all()
    
    @given(st.integers(min_value=1, max_value=5))
    @settings(max_examples=3, deadline=None)
    def test_connection_return_consistency(self, num_operations):
        """**Property 8: 连接归还一致性**
        For any number of get/release operations,
        the pool size should remain consistent
        **Validates: Requirements 6.3**
        """
        config = PoolConfig(min_connections=2, max_connections=5)
        pool = ConnectionPool(self.db_path, config)
        
        try:
            initial_size = pool.size
            
            for _ in range(num_operations):
                conn = pool.get_connection()
                assert conn is not None
                
                # 使用连接
                conn.connection.execute("SELECT 1")
                
                # 释放连接
                pool.release_connection(conn)
            
            # 验证池大小一致
            assert pool.size >= initial_size
            assert pool.in_use_count == 0
        finally:
            pool.close_all()
    
    def test_queue_behavior_under_contention(self):
        """**Property 9: 连接池队列行为**
        When all connections are in use, new requests should wait
        **Validates: Requirements 6.4**
        """
        config = PoolConfig(min_connections=1, max_connections=2, connection_timeout=2.0)
        pool = ConnectionPool(self.db_path, config)
        
        try:
            # 获取所有连接
            conn1 = pool.get_connection()
            conn2 = pool.get_connection()
            
            assert conn1 is not None
            assert conn2 is not None
            assert pool.in_use_count == 2
            
            # 尝试获取第三个连接（应该超时）
            start = time.time()
            conn3 = pool.get_connection(timeout=0.5)
            elapsed = time.time() - start
            
            assert conn3 is None  # 应该超时
            assert elapsed >= 0.4  # 应该等待了接近超时时间
            
            # 释放一个连接后应该能获取
            pool.release_connection(conn1)
            conn3 = pool.get_connection(timeout=1.0)
            assert conn3 is not None
            
            pool.release_connection(conn2)
            pool.release_connection(conn3)
        finally:
            pool.close_all()
    
    def test_connection_reuse(self):
        """测试连接复用"""
        config = PoolConfig(min_connections=1, max_connections=2)
        pool = ConnectionPool(self.db_path, config)
        
        try:
            # 获取并释放连接
            conn1 = pool.get_connection()
            conn1_id = id(conn1)
            pool.release_connection(conn1)
            
            # 再次获取应该复用
            conn2 = pool.get_connection()
            conn2_id = id(conn2)
            
            assert conn1_id == conn2_id
            assert pool._stats['connections_reused'] >= 1
            
            pool.release_connection(conn2)
        finally:
            pool.close_all()
    
    def test_context_manager(self):
        """测试上下文管理器"""
        config = PoolConfig(min_connections=1, max_connections=2)
        pool = ConnectionPool(self.db_path, config)
        
        try:
            with pool.connection() as conn:
                cursor = conn.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1
            
            # 连接应该已释放
            assert pool.in_use_count == 0
        finally:
            pool.close_all()
    
    def test_execute_with_retry(self):
        """测试带重试的执行"""
        config = PoolConfig(min_connections=1, max_connections=2)
        pool = ConnectionPool(self.db_path, config)
        
        try:
            # 插入数据
            pool.execute_with_retry(
                "INSERT INTO test (value) VALUES (?)",
                ("test_value",)
            )
            
            # 查询验证
            with pool.connection() as conn:
                cursor = conn.execute("SELECT value FROM test WHERE value = ?", ("test_value",))
                result = cursor.fetchone()
                assert result[0] == "test_value"
        finally:
            pool.close_all()
    
    def test_concurrent_access(self):
        """测试并发访问"""
        config = PoolConfig(min_connections=2, max_connections=5)
        pool = ConnectionPool(self.db_path, config)
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(5):
                    with pool.connection() as conn:
                        conn.execute(
                            "INSERT INTO test (value) VALUES (?)",
                            (f"worker_{worker_id}_{i}",)
                        )
                        conn.commit()
                        time.sleep(0.01)
                results.append(worker_id)
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        try:
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            assert len(errors) == 0, f"Errors: {errors}"
            assert len(results) == 5
            
            # 验证数据
            with pool.connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM test")
                count = cursor.fetchone()[0]
                assert count == 25  # 5 workers * 5 inserts
        finally:
            pool.close_all()
    
    def test_cleanup_idle_connections(self):
        """测试清理空闲连接"""
        config = PoolConfig(min_connections=1, max_connections=5, idle_timeout=0.1)
        pool = ConnectionPool(self.db_path, config)
        
        try:
            # 创建多个连接
            connections = []
            for _ in range(3):
                conn = pool.get_connection()
                connections.append(conn)
            
            # 释放所有连接
            for conn in connections:
                pool.release_connection(conn)
            
            assert pool.available_count == 3
            
            # 等待超过空闲超时
            time.sleep(0.2)
            
            # 清理
            cleaned = pool.cleanup_idle_connections()
            
            assert cleaned >= 1
            assert pool.available_count < 3
        finally:
            pool.close_all()
    
    def test_get_stats(self):
        """测试获取统计信息"""
        config = PoolConfig(min_connections=2, max_connections=5)
        pool = ConnectionPool(self.db_path, config)
        
        try:
            conn = pool.get_connection()
            pool.release_connection(conn)
            
            stats = pool.get_stats()
            
            assert 'available' in stats
            assert 'in_use' in stats
            assert 'total' in stats
            assert 'max' in stats
            assert 'connections_created' in stats
            assert 'connections_reused' in stats
            
            assert stats['max'] == 5
            assert stats['connections_created'] >= 2
        finally:
            pool.close_all()


class TestPooledConnection:
    """池化连接测试"""
    
    def test_idle_expired(self):
        """测试空闲过期检测"""
        # 创建临时数据库
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        
        try:
            config = PoolConfig(idle_timeout=0.1)
            pool = ConnectionPool(temp_db.name, config)
            
            conn = pool.get_connection()
            conn.mark_released()
            
            # 刚释放不应该过期
            assert not conn.is_idle_expired
            
            # 等待超过空闲超时
            time.sleep(0.15)
            
            assert conn.is_idle_expired
            
            pool.close_all()
        finally:
            os.unlink(temp_db.name)


class TestGlobalPool:
    """全局连接池测试"""
    
    def setup_method(self):
        close_all_pools()
    
    def teardown_method(self):
        close_all_pools()
    
    def test_get_connection_pool_singleton(self):
        """测试单例模式"""
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        
        try:
            pool1 = get_connection_pool(temp_db.name)
            pool2 = get_connection_pool(temp_db.name)
            
            assert pool1 is pool2
        finally:
            close_all_pools()
            os.unlink(temp_db.name)
