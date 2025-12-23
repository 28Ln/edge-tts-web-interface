"""
Edge TTS Web Interface - 主入口
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 在任何其他导入之前加载 .env 文件
from dotenv import load_dotenv
load_dotenv(override=True)

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
    
    # 调试：打印配置
    logger.info(f"AI API Base: {config.ai.api_base}")
    logger.info(f"AI Model: {config.ai.model}")
    logger.info(f"Tencent ID: {config.asr.tencent_secret_id[:10]}..." if config.asr.tencent_secret_id else "Tencent ID: NOT SET")
    
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
    startup_info = f"""
{'=' * 50}
Edge TTS Web Interface v2.0
{'=' * 50}
环境: {config.env}
端口: {config.server.port}
本地访问: http://127.0.0.1:{config.server.port}
{'-' * 50}
API 端点:
  MCU API v1: /mcu/...
  MCU API v2: /v2/mcu/... (带认证)
  微信 API:   /wechat/...
  健康检查:   /health
  API 文档:   /docs
{'-' * 50}
管理面板:
  Dashboard:  /dashboard
  默认密码:   admin123 (请修改 ADMIN_PASSWORD)
{'=' * 50}
"""
    logger.info(startup_info)
    
    # 启动服务
    app.run(
        host=config.server.host,
        port=config.server.port,
        debug=config.server.debug,
    )


if __name__ == "__main__":
    main()
