"""
Admin Dashboard 管理面板
"""

import os
from functools import wraps
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify

from ..auth.models import get_db
from ..auth.api_key import generate_api_key
from ..auth.quota import get_quota_manager
from ..utils.logger import get_logger

logger = get_logger("dashboard")

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# 管理员密码（从环境变量读取）
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('dashboard.login'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== 认证 ====================

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


# ==================== 首页 ====================

@dashboard_bp.route('/')
@login_required
def index():
    """仪表盘首页"""
    import time
    start_time = time.time()
    
    try:
        logger.info("[DASHBOARD] 访问首页")
        
        db = get_db()
        
        # 统计数据
        with db.get_connection() as conn:
            # 用户总数
            user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            
            # 活跃用户数
            active_users = conn.execute('SELECT COUNT(*) FROM users WHERE is_active = 1').fetchone()[0]
            
            # API Key 总数
            key_count = conn.execute('SELECT COUNT(*) FROM api_keys WHERE is_active = 1').fetchone()[0]
            
            # 今日请求数
            today = datetime.now().strftime('%Y-%m-%d')
            today_requests = conn.execute(
                'SELECT COALESCE(SUM(total_requests), 0) FROM daily_usage WHERE date = ?',
                (today,)
            ).fetchone()[0]
            
            # 最近7天请求趋势
            week_data = []
            for i in range(6, -1, -1):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                count = conn.execute(
                    'SELECT COALESCE(SUM(total_requests), 0) FROM daily_usage WHERE date = ?',
                    (date,)
                ).fetchone()[0]
                week_data.append({'date': date[-5:], 'count': count})  # MM-DD 格式
            
            # 最近活跃用户
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
            user_count=0,
            active_users=0,
            key_count=0,
            today_requests=0,
            week_data=[],
            recent_users=[]
        )


# ==================== 用户管理 ====================

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
        import time
        start_time = time.time()
        
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            
            # 验证必填字段
            if not username or not email:
                flash('用户名和邮箱不能为空', 'error')
                return redirect(url_for('dashboard.create_user'))
            
            # 验证用户名格式
            if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
                flash('用户名格式错误，仅支持字母数字下划线，3-30字符', 'error')
                return redirect(url_for('dashboard.create_user'))
            
            # 验证邮箱格式
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                flash('邮箱格式错误', 'error')
                return redirect(url_for('dashboard.create_user'))
            
            # 验证配额参数
            try:
                daily_requests = int(request.form.get('daily_requests', 1000))
                daily_tokens = int(request.form.get('daily_tokens', 100000))
                daily_audio_seconds = int(request.form.get('daily_audio_seconds', 600))
                
                if daily_requests < 0 or daily_tokens < 0 or daily_audio_seconds < 0:
                    flash('配额参数必须为非负整数', 'error')
                    return redirect(url_for('dashboard.create_user'))
            except ValueError:
                flash('配额参数必须为整数', 'error')
                return redirect(url_for('dashboard.create_user'))
            
            logger.info(f"[DASHBOARD] 创建用户请求 | username={username} | email={email}")
            
            db = get_db()
            
            # 检查重复
            if db.get_user_by_username(username):
                logger.warning(f"[DASHBOARD] 用户名已存在 | username={username}")
                flash('用户名已存在', 'error')
                return redirect(url_for('dashboard.create_user'))
            
            user_id = db.create_user(
                username=username,
                email=email,
                daily_requests=daily_requests,
                daily_tokens=daily_tokens,
                daily_audio_seconds=daily_audio_seconds
            )
            
            # 自动生成 API Key
            api_key = generate_api_key()
            db.create_api_key(user_id, api_key, name='default')
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"[DASHBOARD] 创建用户成功 | username={username} | id={user_id} | duration={duration:.2f}ms")
            flash(f'用户创建成功！API Key: {api_key}', 'success')
            return redirect(url_for('dashboard.user_detail', user_id=user_id))
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[DASHBOARD] 创建用户失败 | error={e} | duration={duration:.2f}ms", exc_info=True)
            flash(f'创建失败: {e}', 'error')
    
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
    
    # 获取 API Keys
    keys = db.get_user_api_keys(user_id)
    
    # 获取用量
    manager = get_quota_manager()
    usage = manager.get_usage_summary(user_id)
    
    # 最近7天用量
    with db.get_connection() as conn:
        week_usage = conn.execute('''
            SELECT date, total_requests, total_tokens, total_audio_seconds
            FROM daily_usage
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 7
        ''', (user_id,)).fetchall()
    
    return render_template('dashboard/user_detail.html',
        user=user,
        keys=keys,
        usage=usage,
        week_usage=week_usage
    )


@dashboard_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """编辑用户"""
    import time
    
    db = get_db()
    user = db.get_user(user_id)
    
    if not user:
        logger.warning(f"[DASHBOARD] 用户不存在 | user_id={user_id}")
        flash('用户不存在', 'error')
        return redirect(url_for('dashboard.users'))
    
    if request.method == 'POST':
        start_time = time.time()
        
        try:
            # 验证配额参数
            try:
                daily_requests = int(request.form.get('daily_requests', 1000))
                daily_tokens = int(request.form.get('daily_tokens', 100000))
                daily_audio_seconds = int(request.form.get('daily_audio_seconds', 600))
                
                if daily_requests < 0 or daily_tokens < 0 or daily_audio_seconds < 0:
                    flash('配额参数必须为非负整数', 'error')
                    return redirect(url_for('dashboard.edit_user', user_id=user_id))
            except ValueError:
                flash('配额参数必须为整数', 'error')
                return redirect(url_for('dashboard.edit_user', user_id=user_id))
            
            is_active = request.form.get('is_active') == 'on'
            
            logger.info(f"[DASHBOARD] 更新用户配置 | username={user.username} | user_id={user_id}")
            
            with db.get_connection() as conn:
                conn.execute('''
                    UPDATE users SET 
                        daily_requests = ?,
                        daily_tokens = ?,
                        daily_audio_seconds = ?,
                        is_active = ?
                    WHERE id = ?
                ''', (daily_requests, daily_tokens, daily_audio_seconds, is_active, user_id))
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"[DASHBOARD] 更新用户配置成功 | username={user.username} | duration={duration:.2f}ms")
            flash('用户配置已更新', 'success')
            return redirect(url_for('dashboard.user_detail', user_id=user_id))
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"[DASHBOARD] 更新用户配置失败 | user_id={user_id} | error={e} | duration={duration:.2f}ms", exc_info=True)
            flash(f'更新失败: {e}', 'error')
    
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


# ==================== API Key 管理 ====================

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
    
    # 获取 key 对应的用户
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


# ==================== 用量统计 ====================

@dashboard_bp.route('/usage')
@login_required
def usage():
    """用量统计"""
    db = get_db()
    
    # 获取日期范围
    days = int(request.args.get('days', 7))
    
    with db.get_connection() as conn:
        # 每日汇总
        daily_stats = conn.execute('''
            SELECT date, 
                   SUM(total_requests) as requests,
                   SUM(total_tokens) as tokens,
                   SUM(total_audio_seconds) as audio_seconds
            FROM daily_usage
            WHERE date >= date('now', ?)
            GROUP BY date
            ORDER BY date
        ''', (f'-{days} days',)).fetchall()
        
        # 用户排行
        user_ranking = conn.execute('''
            SELECT u.username, 
                   SUM(d.total_requests) as total_requests,
                   SUM(d.total_tokens) as total_tokens
            FROM users u
            JOIN daily_usage d ON u.id = d.user_id
            WHERE d.date >= date('now', ?)
            GROUP BY u.id
            ORDER BY total_requests DESC
            LIMIT 10
        ''', (f'-{days} days',)).fetchall()
    
    return render_template('dashboard/usage.html',
        daily_stats=daily_stats,
        user_ranking=user_ranking,
        days=days
    )


# ==================== API 接口 ====================

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
            GROUP BY date
            ORDER BY date
        ''', (f'-{days} days',)).fetchall()
    
    return jsonify({
        'labels': [row[0] for row in stats],
        'requests': [row[1] for row in stats],
        'tokens': [row[2] for row in stats]
    })
