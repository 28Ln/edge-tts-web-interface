"""
计费系统定时任务
"""

from datetime import datetime
from typing import Dict

from .service import get_billing_service
from ..utils.logger import get_logger

logger = get_logger("billing.tasks")


def check_expired_subscriptions() -> Dict:
    """
    检查并处理过期订阅
    
    应该每天凌晨运行一次
    
    Returns:
        {"processed": int, "downgraded": int, "timestamp": str}
    """
    logger.info("开始检查过期订阅...")
    
    service = get_billing_service()
    result = service.process_expired_subscriptions()
    
    result["timestamp"] = datetime.now().isoformat()
    
    logger.info(f"过期订阅检查完成: 处理 {result['processed']} 个, 降级 {result['downgraded']} 个")
    
    return result


def reset_daily_usage() -> Dict:
    """
    重置每日用量 (保留历史记录)
    
    应该每天凌晨 00:00 UTC+8 运行
    
    注意: 由于 daily_usage 表是按日期分区的，新的一天会自动创建新记录。
    此函数主要用于清理和归档旧数据。
    
    Returns:
        {"archived_count": int, "timestamp": str}
    """
    logger.info("开始每日用量重置...")
    
    # 获取数据库连接
    from ..auth.models import get_db
    db = get_db()
    
    archived_count = 0
    
    try:
        with db.get_connection() as conn:
            # 获取今天之前的用量记录数 (用于统计)
            from datetime import date, timedelta
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            # 统计昨天的用量记录
            row = conn.execute(
                "SELECT COUNT(*) FROM daily_usage WHERE date = ?",
                (yesterday.isoformat(),)
            ).fetchone()
            archived_count = row[0] if row else 0
            
            logger.info(f"昨日用量记录数: {archived_count}")
            
    except Exception as e:
        logger.error(f"每日用量重置失败: {e}")
    
    result = {
        "archived_count": archived_count,
        "date": datetime.now().date().isoformat(),
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info("每日用量重置完成")
    
    return result


# 如果使用 APScheduler 或其他调度器，可以这样配置：
# 
# from apscheduler.schedulers.background import BackgroundScheduler
# 
# scheduler = BackgroundScheduler()
# 
# # 每天凌晨 1:00 检查过期订阅
# scheduler.add_job(check_expired_subscriptions, 'cron', hour=1, minute=0)
# 
# # 每天凌晨 0:00 重置用量
# scheduler.add_job(reset_daily_usage, 'cron', hour=0, minute=0)
# 
# scheduler.start()


if __name__ == '__main__':
    # 手动运行测试
    print("Running subscription expiry check...")
    result = check_expired_subscriptions()
    print(f"Result: {result}")
