"""
Edge TTS Web Interface - 主入口
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api import create_app
from src.config import get_config, validate_config
from src.utils.logger import setup_logger

logger = setup_logger("main")


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
        logger.warning("FFmpeg 未安装，部分功能可能不可用")
        return False


def check_vosk():
    """检查 Vosk 模型"""
    vosk_path = "vosk-model-small-cn-0.22"
    if os.path.exists(vosk_path):
        logger.info("Vosk 模型已安装")
        return True
    else:
        logger.warning("Vosk 模型未安装，本地语音识别不可用")
        logger.info("下载地址: https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip")
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
    
    # 检查依赖
    check_ffmpeg()
    check_vosk()
    
    # 创建应用
    app = create_app()
    
    # 打印启动信息
    print("=" * 50)
    print("Edge TTS Web Interface")
    print("=" * 50)
    print(f"环境: {config.env}")
    print(f"端口: {config.server.port}")
    print(f"本地访问: http://127.0.0.1:{config.server.port}")
    print("-" * 50)
    print("API 端点:")
    print(f"  MCU API:    /mcu/...")
    print(f"  MCU API v2: /v2/mcu/... (带认证)")
    print(f"  微信 API:   /wechat/...")
    print(f"  健康检查:   /health")
    print(f"  API 文档:   /docs")
    print("=" * 50)
    
    # 启动服务
    app.run(
        host=config.server.host,
        port=config.server.port,
        debug=config.server.debug,
    )


if __name__ == "__main__":
    main()
