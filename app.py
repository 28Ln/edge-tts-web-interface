"""
Edge TTS Web Interface - 入口文件
已迁移到 src/main.py，此文件仅作为兼容入口
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from src.main import main
    main()
