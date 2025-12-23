"""
Dashboard 用量统计
"""

from flask import render_template, request

from . import dashboard_bp
from .auth import login_required
from ...auth.models import get_db


@dashboard_bp.route('/usage')
@login_required
def usage():
    """用量统计"""
    db = get_db()
    days = int(request.args.get('days', 7))
    
    with db.get_connection() as conn:
        daily_stats = conn.execute('''
            SELECT date, 
                   SUM(total_requests) as requests,
                   SUM(total_tokens) as tokens,
                   SUM(total_audio_seconds) as audio_seconds
            FROM daily_usage
            WHERE date >= date('now', ?)
            GROUP BY date ORDER BY date
        ''', (f'-{days} days',)).fetchall()
        
        user_ranking = conn.execute('''
            SELECT u.username, 
                   SUM(d.total_requests) as total_requests,
                   SUM(d.total_tokens) as total_tokens
            FROM users u
            JOIN daily_usage d ON u.id = d.user_id
            WHERE d.date >= date('now', ?)
            GROUP BY u.id ORDER BY total_requests DESC LIMIT 10
        ''', (f'-{days} days',)).fetchall()
    
    return render_template('dashboard/usage.html',
        daily_stats=daily_stats, user_ranking=user_ranking, days=days)
