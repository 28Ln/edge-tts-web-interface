"""
Dashboard API Key 管理
"""

from flask import request, redirect, url_for, flash

from . import dashboard_bp
from .auth import login_required
from ...auth.models import get_db
from ...auth.api_key import generate_api_key
from ...utils.logger import get_logger

logger = get_logger("dashboard.api_keys")


@dashboard_bp.route('/users/<int:user_id>/keys/create', methods=['POST'])
@login_required
def create_key(user_id):
    """创建 API Key"""
    db = get_db()
    user = db.get_user(user_id)
    
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('dashboard.users'))
    
    name = request.form.get('name', 'default')
    permissions = request.form.get('permissions', 'all')
    
    api_key = generate_api_key()
    db.create_api_key(user_id, api_key, name=name, permissions=permissions)
    
    logger.info(f"为用户 {user.username} 创建 API Key: {name}")
    flash(f'API Key 创建成功: {api_key}', 'success')
    
    return redirect(url_for('dashboard.user_detail', user_id=user_id))


@dashboard_bp.route('/keys/<key>/revoke', methods=['POST'])
@login_required
def revoke_key(key):
    """撤销 API Key"""
    db = get_db()
    
    with db.get_connection() as conn:
        row = conn.execute('SELECT user_id FROM api_keys WHERE key = ?', (key,)).fetchone()
        user_id = row[0] if row else None
    
    if db.revoke_api_key(key):
        logger.info(f"撤销 API Key: {key[:12]}...")
        flash('API Key 已撤销', 'success')
    else:
        flash('API Key 不存在', 'error')
    
    if user_id:
        return redirect(url_for('dashboard.user_detail', user_id=user_id))
    return redirect(url_for('dashboard.users'))
