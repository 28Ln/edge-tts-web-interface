"""Gunicorn 生产环境配置

**Feature: production-readiness**
"""

import os
import multiprocessing

# 服务器绑定
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:5000')

# Worker 配置
# 推荐公式: (2 * CPU核心数) + 1
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'sync')
threads = int(os.environ.get('GUNICORN_THREADS', 2))

# 超时配置
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 120))  # 请求超时
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', 30))  # 优雅关闭超时
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', 5))  # Keep-alive 连接超时

# 请求限制
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', 1000))  # Worker 最大请求数后重启
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', 50))  # 随机抖动

# 日志配置
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')  # '-' 表示 stdout
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')  # '-' 表示 stderr
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = 'edge-tts-web'

# 预加载应用（减少内存使用，但热重载不可用）
preload_app = os.environ.get('GUNICORN_PRELOAD', 'false').lower() == 'true'

# 安全配置
limit_request_line = 4094  # 请求行最大长度
limit_request_fields = 100  # 请求头最大数量
limit_request_field_size = 8190  # 单个请求头最大长度

# 临时文件目录
tmp_upload_dir = os.environ.get('GUNICORN_TMP_DIR', None)


def on_starting(server):
    """服务器启动时回调"""
    print(f"Gunicorn 启动中... Workers: {workers}, Bind: {bind}")


def on_reload(server):
    """服务器重载时回调"""
    print("Gunicorn 重载中...")


def worker_int(worker):
    """Worker 收到 SIGINT 时回调"""
    print(f"Worker {worker.pid} 收到中断信号")


def worker_abort(worker):
    """Worker 收到 SIGABRT 时回调"""
    print(f"Worker {worker.pid} 异常终止")


def pre_fork(server, worker):
    """Worker fork 前回调"""
    pass


def post_fork(server, worker):
    """Worker fork 后回调"""
    print(f"Worker {worker.pid} 已启动")


def pre_exec(server):
    """新 master 进程 exec 前回调"""
    print("Gunicorn master 进程重新执行")


def when_ready(server):
    """服务器就绪时回调"""
    print(f"Gunicorn 服务器就绪，监听 {bind}")


def worker_exit(server, worker):
    """Worker 退出时回调"""
    print(f"Worker {worker.pid} 已退出")


def nworkers_changed(server, new_value, old_value):
    """Worker 数量变化时回调"""
    print(f"Worker 数量变化: {old_value} -> {new_value}")


def on_exit(server):
    """服务器退出时回调"""
    print("Gunicorn 服务器关闭")
