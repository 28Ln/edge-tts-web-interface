#!/usr/bin/env python3
"""检查数据库结构"""
import sqlite3

conn = sqlite3.connect('data/auth.db')
conn.row_factory = sqlite3.Row

# 列出所有表
print("Tables:")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(f"  - {t[0]}")

# 检查套餐
print("\nPlans:")
plans = conn.execute("SELECT name, display_name, monthly_price FROM plans").fetchall()
for p in plans:
    print(f"  - {p[0]}: {p[1]} (¥{p[2]})")

# 检查索引
print("\nIndexes:")
indexes = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
for i in indexes:
    print(f"  - {i[0]}")

conn.close()
