"""
资源清理工具
确保临时文件在异常时也能被清理
"""

import os
import tempfile
import atexit
from contextlib import contextmanager
from typing import Optional
from .logger import get_logger

logger = get_logger("cleanup")

# 跟踪需要清理的临时文件
_temp_files = set()


def register_temp_file(filepath: str):
    """注册临时文件，程序退出时自动清理"""
    _temp_files.add(filepath)


def unregister_temp_file(filepath: str):
    """取消注册临时文件"""
    _temp_files.discard(filepath)


def cleanup_temp_files():
    """清理所有注册的临时文件"""
    for filepath in list(_temp_files):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.debug(f"清理临时文件: {filepath}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {filepath} - {e}")
        finally:
            _temp_files.discard(filepath)


# 注册退出时清理
atexit.register(cleanup_temp_files)


@contextmanager
def temp_file(suffix: str = "", prefix: str = "tmp_", dir: str = None):
    """
    临时文件上下文管理器
    
    Usage:
        with temp_file(suffix=".wav") as filepath:
            # 使用临时文件
            save_audio(filepath)
            process_audio(filepath)
        # 自动清理
    """
    fd, filepath = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
    os.close(fd)
    register_temp_file(filepath)
    
    try:
        yield filepath
    finally:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {filepath} - {e}")
        finally:
            unregister_temp_file(filepath)


@contextmanager
def temp_directory(prefix: str = "tmp_", dir: str = None):
    """
    临时目录上下文管理器
    
    Usage:
        with temp_directory() as dirpath:
            # 使用临时目录
            save_files(dirpath)
        # 自动清理
    """
    import shutil
    dirpath = tempfile.mkdtemp(prefix=prefix, dir=dir)
    
    try:
        yield dirpath
    finally:
        try:
            if os.path.exists(dirpath):
                shutil.rmtree(dirpath)
                logger.debug(f"清理临时目录: {dirpath}")
        except Exception as e:
            logger.warning(f"清理临时目录失败: {dirpath} - {e}")


def cleanup_old_files(directory: str, max_age_hours: int = 24, pattern: str = "*"):
    """
    清理过期文件
    
    Args:
        directory: 目录路径
        max_age_hours: 最大保留时间（小时）
        pattern: 文件匹配模式
    """
    import glob
    import time
    
    if not os.path.exists(directory):
        return
    
    max_age_seconds = max_age_hours * 3600
    current_time = time.time()
    cleaned = 0
    
    for filepath in glob.glob(os.path.join(directory, pattern)):
        try:
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > max_age_seconds:
                    os.remove(filepath)
                    cleaned += 1
        except Exception as e:
            logger.warning(f"清理文件失败: {filepath} - {e}")
    
    if cleaned > 0:
        logger.info(f"清理了 {cleaned} 个过期文件 ({directory})")
