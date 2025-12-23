"""
Dashboard 首页模块
"""

import time
from datetime import datetime, timedelta
from flask import render_template, flash

from . import dashboard_bp
from .auth import login_required
from ...auth.models import get_db
from ...utils.logger import get_logger

logger = get_logger("dashboard.home")


@dashboard_bp.route('/')
@login_required
def index():
    """仪表盘首页"""
    start_time = time.time()
    
    try:
        logger.info("[DASHBOARD] 访问首页")
        
        db = get_db()
        
        with db.get_connection() as conn:
            user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            active_users = conn.execute('SELECT COUNT(*) FROM users WHERE is_active = 1').fetchone()[0]
            key_count = conn.execute('SELECT COUNT(*) FROM api_keys WHERE is_active = 1').fetchone()[0]
            
            today = datetime.now().strftime('%Y-%m-%d')
            today_requests = conn.execute(
                'SELECT COALESCE(SUM(total_requests), 0) FROM daily_usage WHERE date = ?',
                (today,)
            ).fetchone()[0]
            
            week_data = []
            for i in range(6, -1, -1):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                count = conn.execute(
                    'SELECT COALESCE(SUM(total_requests), 0) FROM daily_usage WHERE date = ?',
                    (date,)
                ).fetchone()[0]
                week_data.append({'date': date[-5:], 'count': count})
            
            recent_users = conn.execute('''
                SELECT u.username, u.email, COALESCE(d.total_requests, 0) as today_requests
                FROM users u
                LEFT JOIN daily_usage d ON u.id = d.user_id AND d.date = ?
                ORDER BY today_requests DESC
                LIMIT 5
            ''', (today,)).fetchall()
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"[DASHBOARD] 首页加载完成 | duration={duration:.2f}ms")
        
        return render_template('dashboard/index.html',
            user_count=user_count,
            active_users=active_users,
            key_count=key_count,
            today_requests=today_requests,
            week_data=week_data,
            recent_users=recent_users
        )
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"[DASHBOARD] 首页加载失败 | error={e} | duration={duration:.2f}ms", exc_info=True)
        flash('加载数据失败，请稍后重试', 'error')
        return render_template('dashboard/index.html',
            user_count=0, active_users=0, key_count=0,
            today_requests=0, week_data=[], recent_users=[]
        )
