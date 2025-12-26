"""健康检查状态管理

**Feature: production-readiness**
"""

import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from threading import Lock
from enum import Enum

from src.utils.logger import get_logger


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """服务健康状态"""
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    consecutive_failures: int = 0
    last_check_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_error: Optional[str] = None
    
    # 配置
    failure_threshold: int = 3  # 连续失败次数阈值
    recovery_threshold: int = 2  # 恢复所需连续成功次数
    consecutive_successes: int = 0


class HealthChecker:
    """健康检查管理器
    
    实现连续失败计数和状态转换逻辑
    """
    
    def __init__(self, failure_threshold: int = 3, recovery_threshold: int = 2):
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold
        self.logger = get_logger('health_checker')
        
        self._lock = Lock()
        self._services: Dict[str, ServiceHealth] = {}
        self._check_functions: Dict[str, Callable[[], bool]] = {}
        
        self.logger.info(
            f"健康检查器初始化: failure_threshold={failure_threshold}, "
            f"recovery_threshold={recovery_threshold}"
        )
    
    def register_service(
        self, 
        name: str, 
        check_func: Callable[[], bool],
        failure_threshold: int = None,
        recovery_threshold: int = None
    ) -> None:
        """注册服务健康检查
        
        Args:
            name: 服务名称
            check_func: 检查函数，返回 True 表示健康
            failure_threshold: 自定义失败阈值
            recovery_threshold: 自定义恢复阈值
        """
        with self._lock:
            self._services[name] = ServiceHealth(
                name=name,
                failure_threshold=failure_threshold or self.failure_threshold,
                recovery_threshold=recovery_threshold or self.recovery_threshold
            )
            self._check_functions[name] = check_func
            
            self.logger.debug(f"注册服务健康检查: {name}")
    
    def check_service(self, name: str) -> ServiceHealth:
        """执行单个服务的健康检查
        
        Args:
            name: 服务名称
            
        Returns:
            ServiceHealth: 服务健康状态
        """
        with self._lock:
            if name not in self._services:
                raise ValueError(f"未注册的服务: {name}")
            
            service = self._services[name]
            check_func = self._check_functions[name]
            
            service.last_check_time = time.time()
            
            try:
                is_healthy = check_func()
                
                if is_healthy:
                    self._handle_success(service)
                else:
                    self._handle_failure(service, "检查返回 False")
                    
            except Exception as e:
                self._handle_failure(service, str(e))
            
            return service
    
    def _handle_success(self, service: ServiceHealth) -> None:
        """处理检查成功"""
        service.last_success_time = time.time()
        service.last_error = None
        service.consecutive_successes += 1
        
        if service.status == HealthStatus.UNHEALTHY:
            # 从不健康恢复需要连续成功
            if service.consecutive_successes >= service.recovery_threshold:
                old_status = service.status
                service.status = HealthStatus.HEALTHY
                service.consecutive_failures = 0
                
                self.logger.info(
                    f"服务 {service.name} 恢复健康: "
                    f"{old_status.value} -> {service.status.value}"
                )
        elif service.status == HealthStatus.DEGRADED:
            # 从降级恢复
            service.status = HealthStatus.HEALTHY
            service.consecutive_failures = 0
            
            self.logger.info(f"服务 {service.name} 恢复健康")
        else:
            # 保持健康
            service.status = HealthStatus.HEALTHY
            service.consecutive_failures = 0
    
    def _handle_failure(self, service: ServiceHealth, error: str) -> None:
        """处理检查失败"""
        service.last_error = error
        service.consecutive_failures += 1
        service.consecutive_successes = 0
        
        old_status = service.status
        
        if service.consecutive_failures >= service.failure_threshold:
            service.status = HealthStatus.UNHEALTHY
        elif service.consecutive_failures >= 1:
            service.status = HealthStatus.DEGRADED
        
        if old_status != service.status:
            self.logger.warning(
                f"服务 {service.name} 状态变更: "
                f"{old_status.value} -> {service.status.value}, "
                f"连续失败: {service.consecutive_failures}, 错误: {error}"
            )
    
    def check_all(self) -> Dict[str, ServiceHealth]:
        """检查所有注册的服务
        
        Returns:
            Dict[str, ServiceHealth]: 所有服务的健康状态
        """
        results = {}
        
        for name in list(self._services.keys()):
            results[name] = self.check_service(name)
        
        return results
    
    def get_service_status(self, name: str) -> Optional[ServiceHealth]:
        """获取服务状态（不执行检查）"""
        with self._lock:
            return self._services.get(name)
    
    def get_overall_status(self) -> HealthStatus:
        """获取整体健康状态
        
        Returns:
            HealthStatus: 整体状态（取最差的服务状态）
        """
        with self._lock:
            return self._get_overall_status_unlocked()
    
    def _get_overall_status_unlocked(self) -> HealthStatus:
        """获取整体健康状态（内部方法，不加锁）"""
        if not self._services:
            return HealthStatus.UNKNOWN
        
        statuses = [s.status for s in self._services.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif HealthStatus.UNKNOWN in statuses:
            return HealthStatus.UNKNOWN
        else:
            return HealthStatus.HEALTHY
    
    def get_summary(self) -> Dict[str, Any]:
        """获取健康检查摘要"""
        with self._lock:
            services_summary = {}
            
            for name, service in self._services.items():
                services_summary[name] = {
                    'status': service.status.value,
                    'consecutive_failures': service.consecutive_failures,
                    'last_check_time': service.last_check_time,
                    'last_success_time': service.last_success_time,
                    'last_error': service.last_error
                }
            
            return {
                'overall_status': self._get_overall_status_unlocked().value,
                'services': services_summary,
                'total_services': len(self._services),
                'healthy_count': sum(
                    1 for s in self._services.values() 
                    if s.status == HealthStatus.HEALTHY
                ),
                'unhealthy_count': sum(
                    1 for s in self._services.values() 
                    if s.status == HealthStatus.UNHEALTHY
                )
            }
    
    def reset_service(self, name: str) -> None:
        """重置服务状态"""
        with self._lock:
            if name in self._services:
                service = self._services[name]
                service.status = HealthStatus.UNKNOWN
                service.consecutive_failures = 0
                service.consecutive_successes = 0
                service.last_error = None
    
    def reset_all(self) -> None:
        """重置所有服务状态"""
        with self._lock:
            for name in self._services:
                self.reset_service(name)


# 全局健康检查器实例
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """获取全局健康检查器实例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def reset_health_checker() -> None:
    """重置全局健康检查器（主要用于测试）"""
    global _health_checker
    _health_checker = None
