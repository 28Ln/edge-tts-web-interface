#!/usr/bin/env python3
"""
数据库迁移运行脚本
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = os.environ.get('AUTH_DB_PATH', 'data/auth.db')
MIGRATIONS_DIR = PROJECT_ROOT / 'migrations'


def get_applied_migrations(conn) -> set:
    """获取已应用的迁移"""
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        rows = conn.execute('SELECT name FROM _migrations').fetchall()
        return {row[0] for row in rows}
    except Exception:
        return set()


def apply_migration(conn, migration_file: Path) -> bool:
    """应用单个迁移"""
    migration_name = migration_file.stem
    
    print(f"  Applying: {migration_name}...")
    
    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        conn.executescript(sql)
        conn.execute(
            'INSERT INTO _migrations (name) VALUES (?)',
            (migration_name,)
        )
        conn.commit()
        print(f"  ✓ Applied: {migration_name}")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {migration_name} - {e}")
        conn.rollback()
        return False


def ensure_user_columns(conn):
    """确保用户表有计费所需的字段"""
    try:
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'balance' not in columns:
            conn.execute('ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0')
            print("  ✓ Added column: users.balance")
        
        if 'email_verified' not in columns:
            conn.execute('ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0')
            print("  ✓ Added column: users.email_verified")
        
        if 'password_hash' not in columns:
            conn.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')
            print("  ✓ Added column: users.password_hash")
        
        conn.commit()
    except Exception as e:
        print(f"  Warning: Could not update users table - {e}")


def run_migrations():
    """运行所有待执行的迁移"""
    print(f"\n{'='*50}")
    print("Database Migration")
    print(f"{'='*50}")
    print(f"Database: {DB_PATH}")
    print(f"Migrations: {MIGRATIONS_DIR}")
    print()
    
    # 确保数据目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # 获取已应用的迁移
        applied = get_applied_migrations(conn)
        print(f"Applied migrations: {len(applied)}")
        
        # 获取所有迁移文件
        migration_files = sorted(MIGRATIONS_DIR.glob('*.sql'))
        print(f"Total migrations: {len(migration_files)}")
        print()
        
        # 应用新迁移
        new_count = 0
        for migration_file in migration_files:
            if migration_file.stem not in applied:
                if apply_migration(conn, migration_file):
                    new_count += 1
                else:
                    print("\nMigration failed, stopping.")
                    return False
        
        # 确保用户表有必要的字段
        print("\nChecking user table columns...")
        ensure_user_columns(conn)
        
        print(f"\n{'='*50}")
        if new_count > 0:
            print(f"✓ Applied {new_count} new migration(s)")
        else:
            print("✓ Database is up to date")
        print(f"{'='*50}\n")
        
        return True
        
    finally:
        conn.close()


def show_status():
    """显示迁移状态"""
    if not os.path.exists(DB_PATH):
        print("Database does not exist yet.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        applied = get_applied_migrations(conn)
        migration_files = sorted(MIGRATIONS_DIR.glob('*.sql'))
        
        print(f"\nMigration Status:")
        print(f"{'-'*50}")
        
        for migration_file in migration_files:
            name = migration_file.stem
            status = "✓ Applied" if name in applied else "○ Pending"
            print(f"  {status}: {name}")
        
        print(f"{'-'*50}")
        print(f"Total: {len(migration_files)}, Applied: {len(applied)}, Pending: {len(migration_files) - len(applied)}")
        
    finally:
        conn.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        show_status()
    else:
        success = run_migrations()
        sys.exit(0 if success else 1)
