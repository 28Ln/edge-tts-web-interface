"""
Dashboard API 接口
"""

from flask import request, jsonify

from . import dashboard_bp
from .auth import login_required
from ...auth.models import get_db


@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    """获取统计数据 API"""
    db = get_db()
    days = int(request.args.get('days', 7))
    
    with db.get_connection() as conn:
        stats = conn.execute('''
            SELECT date, 
                   SUM(total_requests) as requests,
                   SUM(total_tokens) as tokens
            FROM daily_usage
            WHERE date >= date('now', ?)
            GROUP BY date ORDER BY date
        ''', (f'-{days} days',)).fetchall()
    
    return jsonify({
        'labels': [row[0] for row in stats],
        'requests': [row[1] for row in stats],
        'tokens': [row[2] for row in stats]
    })
