"""
WebSocket 模块
"""

from .socketio import init_socketio
from .native import init_native_websocket
from .test_page import get_realtime_test_page

__all__ = ['init_socketio', 'init_native_websocket', 'get_realtime_test_page']
