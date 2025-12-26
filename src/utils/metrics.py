"""Prometheus 指标收集

**Feature: production-readiness**
"""

import time
import os
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from threading import Lock
from collections import defaultdict

from src.utils.logger import get_logger


@dataclass
class HistogramBucket:
    """直方图桶"""
    le: float  # 上界
    count: int = 0


class MetricsCollector:
    """Prometheus 指标收集器
    
    实现简单的 Prometheus 格式指标收集，无需外部依赖
    """
    
    # 延迟直方图桶边界（毫秒）
    LATENCY_BUCKETS = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
    
    def __init__(self):
        self._lock = Lock()
        self.logger = get_logger('metrics')
        
        # Counter: 请求计数
        self._request_count: Dict[str, int] = defaultdict(int)
        
        # Histogram: 请求延迟
        self._request_latency_sum: Dict[str, float] = defaultdict(float)
        self._request_latency_count: Dict[str, int] = defaultdict(int)
        self._request_latency_buckets: Dict[str, List[HistogramBucket]] = {}
        
        # Gauge: 活跃连接数
        self._active_connections: int = 0
        
        # Gauge: 服务状态 (1=healthy, 0=unhealthy)
        self._service_status: Dict[str, int] = {
            'database': 1,
            'ai_service': 1,
            'tts_service': 1,
            'asr_service': 1
        }
        
        # Counter: 错误计数
        self._error_count: Dict[str, int] = defaultdict(int)
        
        self.logger.info("Prometheus 指标收集器初始化完成")
    
    def inc_request_count(self, method: str, endpoint: str, status_code: int) -> None:
        """增加请求计数
        
        Args:
            method: HTTP 方法
            endpoint: 端点路径
            status_code: HTTP 状态码
        """
        with self._lock:
            key = f"{method}|{endpoint}|{status_code}"
            self._request_count[key] += 1
    
    def observe_latency(self, method: str, endpoint: str, latency_ms: float) -> None:
        """记录请求延迟
        
        Args:
            method: HTTP 方法
            endpoint: 端点路径
            latency_ms: 延迟（毫秒）
        """
        with self._lock:
            key = f"{method}|{endpoint}"
            
            # 更新 sum 和 count
            self._request_latency_sum[key] += latency_ms
            self._request_latency_count[key] += 1
            
            # 更新桶
            if key not in self._request_latency_buckets:
                self._request_latency_buckets[key] = [
                    HistogramBucket(le=b) for b in self.LATENCY_BUCKETS
                ]
                self._request_latency_buckets[key].append(
                    HistogramBucket(le=float('inf'))
                )
            
            for bucket in self._request_latency_buckets[key]:
                if latency_ms <= bucket.le:
                    bucket.count += 1
    
    def inc_active_connections(self) -> None:
        """增加活跃连接数"""
        with self._lock:
            self._active_connections += 1
    
    def dec_active_connections(self) -> None:
        """减少活跃连接数"""
        with self._lock:
            self._active_connections = max(0, self._active_connections - 1)
    
    def set_service_status(self, service: str, healthy: bool) -> None:
        """设置服务状态
        
        Args:
            service: 服务名称
            healthy: 是否健康
        """
        with self._lock:
            self._service_status[service] = 1 if healthy else 0
    
    def inc_error_count(self, error_type: str) -> None:
        """增加错误计数
        
        Args:
            error_type: 错误类型
        """
        with self._lock:
            self._error_count[error_type] += 1
    
    def get_request_count(self, method: str = None, endpoint: str = None) -> int:
        """获取请求计数
        
        Args:
            method: HTTP 方法（可选）
            endpoint: 端点路径（可选）
            
        Returns:
            int: 请求计数
        """
        with self._lock:
            if method is None and endpoint is None:
                return sum(self._request_count.values())
            
            total = 0
            for key, count in self._request_count.items():
                parts = key.split('|')
                if len(parts) >= 2:
                    if method and parts[0] != method:
                        continue
                    if endpoint and parts[1] != endpoint:
                        continue
                    total += count
            return total

    def export_prometheus_format(self) -> str:
        """导出 Prometheus 格式的指标
        
        Returns:
            str: Prometheus 格式的指标文本
        """
        with self._lock:
            lines = []
            
            # 请求计数
            lines.append("# HELP http_requests_total Total number of HTTP requests")
            lines.append("# TYPE http_requests_total counter")
            for key, count in self._request_count.items():
                parts = key.split('|')
                if len(parts) >= 3:
                    method, endpoint, status = parts[0], parts[1], parts[2]
                    lines.append(
                        f'http_requests_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}'
                    )
            
            # 请求延迟直方图
            lines.append("")
            lines.append("# HELP http_request_duration_ms HTTP request duration in milliseconds")
            lines.append("# TYPE http_request_duration_ms histogram")
            for key, buckets in self._request_latency_buckets.items():
                parts = key.split('|')
                if len(parts) >= 2:
                    method, endpoint = parts[0], parts[1]
                    for bucket in buckets:
                        le = "+Inf" if bucket.le == float('inf') else str(bucket.le)
                        lines.append(
                            f'http_request_duration_ms_bucket{{method="{method}",endpoint="{endpoint}",le="{le}"}} {bucket.count}'
                        )
                    lines.append(
                        f'http_request_duration_ms_sum{{method="{method}",endpoint="{endpoint}"}} {self._request_latency_sum[key]}'
                    )
                    lines.append(
                        f'http_request_duration_ms_count{{method="{method}",endpoint="{endpoint}"}} {self._request_latency_count[key]}'
                    )
            
            # 活跃连接数
            lines.append("")
            lines.append("# HELP http_active_connections Current number of active connections")
            lines.append("# TYPE http_active_connections gauge")
            lines.append(f"http_active_connections {self._active_connections}")
            
            # 服务状态
            lines.append("")
            lines.append("# HELP service_status Service health status (1=healthy, 0=unhealthy)")
            lines.append("# TYPE service_status gauge")
            for service, status in self._service_status.items():
                lines.append(f'service_status{{service="{service}"}} {status}')
            
            # 错误计数
            lines.append("")
            lines.append("# HELP http_errors_total Total number of HTTP errors")
            lines.append("# TYPE http_errors_total counter")
            for error_type, count in self._error_count.items():
                lines.append(f'http_errors_total{{type="{error_type}"}} {count}')
            
            return "\n".join(lines)
    
    def get_stats(self) -> Dict:
        """获取统计摘要
        
        Returns:
            Dict: 统计信息
        """
        with self._lock:
            total_requests = sum(self._request_count.values())
            total_errors = sum(self._error_count.values())
            
            return {
                'total_requests': total_requests,
                'total_errors': total_errors,
                'active_connections': self._active_connections,
                'service_status': dict(self._service_status),
                'error_rate': total_errors / total_requests if total_requests > 0 else 0
            }
    
    def reset(self) -> None:
        """重置所有指标（主要用于测试）"""
        with self._lock:
            self._request_count.clear()
            self._request_latency_sum.clear()
            self._request_latency_count.clear()
            self._request_latency_buckets.clear()
            self._active_connections = 0
            self._service_status = {
                'database': 1,
                'ai_service': 1,
                'tts_service': 1,
                'asr_service': 1
            }
            self._error_count.clear()


# 全局指标收集器实例
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector() -> None:
    """重置全局指标收集器（主要用于测试）"""
    global _metrics_collector
    if _metrics_collector:
        _metrics_collector.reset()
    _metrics_collector = None
