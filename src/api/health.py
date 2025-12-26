"""
健康检查 API
"""

from flask import Blueprint, jsonify, Response
from datetime import datetime
import os

from ..services.asr_service import get_asr_service
from ..config import get_config
from ..utils.metrics import get_metrics_collector

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health():
    """
    健康检查接口
    
    返回服务健康状态，用于负载均衡器和监控系统
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    })


@health_bp.route('/health/ready', methods=['GET'])
def ready():
    """
    就绪检查接口
    
    检查所有依赖服务是否就绪
    """
    checks = {}
    all_ready = True
    
    # 检查 ASR 服务
    try:
        asr_service = get_asr_service()
        engines = asr_service.get_available_engines()
        checks["asr"] = {
            "status": "ready" if any(engines.values()) else "degraded",
            "engines": engines,
        }
        if not any(engines.values()):
            all_ready = False
    except Exception as e:
        checks["asr"] = {"status": "error", "message": str(e)}
        all_ready = False
    
    # 检查 AI 配置
    config = get_config()
    ai_configured = bool(config.ai.api_base and config.ai.api_key)
    checks["ai"] = {
        "status": "ready" if ai_configured else "not_configured",
        "model": config.ai.model if ai_configured else None,
    }
    if not ai_configured:
        all_ready = False
    
    # 检查 FFmpeg
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        checks["ffmpeg"] = {"status": "ready"}
    except:
        checks["ffmpeg"] = {"status": "not_available"}
        # FFmpeg 不是必须的，不影响整体就绪状态
    
    status_code = 200 if all_ready else 503
    return jsonify({
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }), status_code


@health_bp.route('/health/live', methods=['GET'])
def live():
    """
    存活检查接口
    
    简单返回，表示服务进程存活
    """
    return jsonify({
        "status": "alive",
        "pid": os.getpid(),
    })


@health_bp.route('/version', methods=['GET'])
def version():
    """
    版本信息接口
    """
    return jsonify({
        "name": "Edge TTS Web Interface",
        "version": "2.0.0",
        "api_version": "v2",
    })


@health_bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Prometheus 指标端点
    
    返回 Prometheus 格式的指标数据
    """
    collector = get_metrics_collector()
    metrics_output = collector.export_prometheus_format()
    
    return Response(
        metrics_output,
        mimetype='text/plain; charset=utf-8'
    )


@health_bp.route('/metrics/stats', methods=['GET'])
def metrics_stats():
    """
    指标统计摘要端点
    
    返回 JSON 格式的统计摘要
    """
    collector = get_metrics_collector()
    stats = collector.get_stats()
    
    return jsonify({
        "success": True,
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    })
