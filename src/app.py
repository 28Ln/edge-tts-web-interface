"""
应用入口
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api import create_app
from src.config import get_config, validate_config
from src.utils.logger import setup_logger

logger = setup_logger("app")


def check_ffmpeg():
    """检查 FFmpeg"""
    import subprocess
    
    # 检查本地 ffmpeg
    local_ffmpeg = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "ffmpeg", "ffmpeg-master-latest-win64-gpl", "bin"
    )
    if os.path.exists(local_ffmpeg):
        os.environ["PATH"] = local_ffmpeg + os.pathsep + os.environ.get("PATH", "")
        logger.info(f"使用本地 FFmpeg: {local_ffmpeg}")
    
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
        logger.info("FFmpeg 已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("FFmpeg 未安装")
        return False


def main():
    """主函数"""
    # 加载配置
    config = get_config()
    
    # 验证配置
    errors = validate_config(config)
    if errors:
        for error in errors:
            logger.warning(f"配置警告: {error}")
    
    # 检查 FFmpeg
    check_ffmpeg()
    
    # 创建应用
    app = create_app()
    
    # 打印启动信息
    print("=" * 50)
    print("Edge TTS Web Interface")
    print("=" * 50)
    print(f"端口: {config.server.port}")
    print(f"本地访问: http://127.0.0.1:{config.server.port}")
    print(f"MCU API: /mcu/...")
    print("=" * 50)
    
    # 启动服务
    app.run(
        host=config.server.host,
        port=config.server.port,
        debug=config.server.debug,
    )


if __name__ == "__main__":
    main()
