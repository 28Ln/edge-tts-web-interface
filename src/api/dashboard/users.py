"""
Dashboard 用户管理
"""

from datetime import datetime
from flask import render_template, request, redirect, url_for, flash

from . import dashboard_bp
from .auth import login_required
from ...auth.models import get_db
from ...auth.api_key import generate_api_key
from ...auth.quota import get_quota_manager
from ...utils.logger import get_logger

logger = get_logger("dashboard.users")


@dashboard_bp.route('/users')
@login_required
def users():
    """用户列表"""
    db = get_db()
    
    with db.get_connection() as conn:
        users_list = conn.execute('''
            SELECT u.*, 
                   COUNT(k.id) as key_count,
                   COALESCE(d.total_requests, 0) as today_requests
            FROM users u
            LEFT JOIN api_keys k ON u.id = k.user_id AND k.is_active = 1
            LEFT JOIN daily_usage d ON u.id = d.user_id AND d.date = ?
            GROUP BY u.id
            ORDER BY u.created_at DESC
        ''', (datetime.now().strftime('%Y-%m-%d'),)).fetchall()
    
    return render_template('dashboard/users.html', users=users_list)


@dashboard_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    """创建用户"""
    if request.method == 'POST':
        import re
        
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        
        if not username or not email:
            flash('用户名和邮箱不能为空', 'error')
            return redirect(url_for('dashboard.create_user'))
        
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
            flash('用户名格式错误', 'error')
            return redirect(url_for('dashboard.create_user'))
        
        db = get_db()
        
        if db.get_user_by_username(username):
            flash('用户名已存在', 'error')
            return redirect(url_for('dashboard.create_user'))
        
        try:
            daily_requests = int(request.form.get('daily_requests', 1000))
            daily_tokens = int(request.form.get('daily_tokens', 100000))
            daily_audio_seconds = int(request.form.get('daily_audio_seconds', 600))
        except ValueError:
            flash('配额参数必须为整数', 'error')
            return redirect(url_for('dashboard.create_user'))
        
        user_id = db.create_user(
            username=username,
            email=email,
            daily_requests=daily_requests,
            daily_tokens=daily_tokens,
            daily_audio_seconds=daily_audio_seconds
        )
        
        api_key = generate_api_key()
        db.create_api_key(user_id, api_key, name='default')
        
        logger.info(f"创建用户成功: {username}")
        flash(f'用户创建成功！API Key: {api_key}', 'success')
        return redirect(url_for('dashboard.user_detail', user_id=user_id))
    
    return render_template('dashboard/user_form.html', user=None)


@dashboard_bp.route('/users/<int:user_id>')
@login_required
def user_detail(user_id):
    """用户详情"""
    db = get_db()
    user = db.get_user(user_id)
    
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('dashboard.users'))
    
    keys = db.get_user_api_keys(user_id)
    manager = get_quota_manager()
    usage = manager.get_usage_summary(user_id)
    
    with db.get_connection() as conn:
        week_usage = conn.execute('''
            SELECT date, total_requests, total_tokens, total_audio_seconds
            FROM daily_usage WHERE user_id = ?
            ORDER BY date DESC LIMIT 7
        ''', (user_id,)).fetchall()
    
    return render_template('dashboard/user_detail.html',
        user=user, keys=keys, usage=usage, week_usage=week_usage)


@dashboard_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """编辑用户"""
    db = get_db()
    user = db.get_user(user_id)
    
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('dashboard.users'))
    
    if request.method == 'POST':
        try:
            daily_requests = int(request.form.get('daily_requests', 1000))
            daily_tokens = int(request.form.get('daily_tokens', 100000))
            daily_audio_seconds = int(request.form.get('daily_audio_seconds', 600))
        except ValueError:
            flash('配额参数必须为整数', 'error')
            return redirect(url_for('dashboard.edit_user', user_id=user_id))
        
        is_active = request.form.get('is_active') == 'on'
        
        with db.get_connection() as conn:
            conn.execute('''
                UPDATE users SET daily_requests = ?, daily_tokens = ?,
                daily_audio_seconds = ?, is_active = ? WHERE id = ?
            ''', (daily_requests, daily_tokens, daily_audio_seconds, is_active, user_id))
        
        logger.info(f"更新用户配置: {user.username}")
        flash('用户配置已更新', 'success')
        return redirect(url_for('dashboard.user_detail', user_id=user_id))
    
    return render_template('dashboard/user_form.html', user=user)


@dashboard_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
def toggle_user(user_id):
    """启用/禁用用户"""
    db = get_db()
    user = db.get_user(user_id)
    
    if user:
        new_status = not user.is_active
        with db.get_connection() as conn:
            conn.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
        
        status_text = '启用' if new_status else '禁用'
        logger.info(f"用户 {user.username} 已{status_text}")
        flash(f'用户已{status_text}', 'success')
    
    return redirect(url_for('dashboard.users'))
