"""
Dashboard 认证模块
"""

import os
from functools import wraps
from datetime import datetime
from flask import request, redirect, url_for, session, flash, render_template

from . import dashboard_bp
from ...utils.logger import get_logger

logger = get_logger("dashboard.auth")

# 管理员密码（从环境变量读取）
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('dashboard.login'))
        return f(*args, **kwargs)
    return decorated_function


@dashboard_bp.route('/login', methods=['GET', 'POST'])
def login():
    """管理员登录"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['login_time'] = datetime.now().isoformat()
            logger.info("管理员登录成功")
            return redirect(url_for('dashboard.index'))
        else:
            flash('密码错误', 'error')
            logger.warning("管理员登录失败：密码错误")
    
    return render_template('dashboard/login.html')


@dashboard_bp.route('/logout')
def logout():
    """登出"""
    session.clear()
    flash('已退出登录', 'success')
    return redirect(url_for('dashboard.login'))
