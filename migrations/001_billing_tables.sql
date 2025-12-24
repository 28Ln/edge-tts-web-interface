-- 计费系统数据库迁移脚本
-- Migration: 001_billing_tables
-- Description: 创建计费系统所需的所有表和索引
-- Requirements: 1.1, 1.3, 2.1, 5.1

-- ============================================
-- 1. 套餐表 (plans)
-- ============================================
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,              -- 套餐标识: free, basic, pro, enterprise
    display_name TEXT NOT NULL,             -- 显示名称: 免费版, 基础版, 专业版, 企业版
    description TEXT DEFAULT '',            -- 套餐描述
    monthly_price REAL DEFAULT 0,           -- 月费 (元)
    
    -- 配额限制
    daily_requests INTEGER DEFAULT 100,     -- 每日请求数限制
    daily_tokens INTEGER DEFAULT 10000,     -- 每日Token数限制
    daily_audio_seconds INTEGER DEFAULT 60, -- 每日音频秒数限制
    
    -- 按量计费价格 (元)
    price_per_request REAL DEFAULT 0,       -- 每次请求价格
    price_per_1k_tokens REAL DEFAULT 0,     -- 每1000 Token价格
    price_per_minute_audio REAL DEFAULT 0,  -- 每分钟音频价格
    
    -- 状态
    is_active BOOLEAN DEFAULT 1,            -- 是否启用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 2. 订阅表 (subscriptions)
-- ============================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,               -- 用户ID
    plan_id INTEGER NOT NULL,               -- 套餐ID
    status TEXT DEFAULT 'active',           -- 状态: active, expired, cancelled
    start_date TIMESTAMP NOT NULL,          -- 开始日期
    end_date TIMESTAMP,                     -- 结束日期 (NULL表示永久)
    auto_renew BOOLEAN DEFAULT 0,           -- 是否自动续费
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES plans(id)
);

-- ============================================
-- 3. 交易记录表 (transactions)
-- ============================================
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,               -- 用户ID
    type TEXT NOT NULL,                     -- 类型: recharge, consume, refund, subscribe
    amount REAL NOT NULL,                   -- 金额 (正数增加，负数减少)
    balance_after REAL,                     -- 交易后余额
    description TEXT DEFAULT '',            -- 描述
    reference_id TEXT,                      -- 外部订单号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================
-- 4. 管理员表 (admins)
-- ============================================
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,          -- 管理员用户名
    password_hash TEXT NOT NULL,            -- 密码哈希
    api_key TEXT UNIQUE,                    -- Admin API Key
    is_super BOOLEAN DEFAULT 0,             -- 是否超级管理员
    is_active BOOLEAN DEFAULT 1,            -- 是否启用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- ============================================
-- 5. 索引
-- ============================================

-- 套餐索引
CREATE INDEX IF NOT EXISTS idx_plans_name ON plans(name);
CREATE INDEX IF NOT EXISTS idx_plans_active ON plans(is_active);
CREATE INDEX IF NOT EXISTS idx_plans_price ON plans(monthly_price);

-- 订阅索引
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status ON subscriptions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_end_date ON subscriptions(end_date);

-- 交易索引
CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_user_type ON transactions(user_id, type);
CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_reference ON transactions(reference_id);

-- 管理员索引
CREATE INDEX IF NOT EXISTS idx_admins_api_key ON admins(api_key);
CREATE INDEX IF NOT EXISTS idx_admins_username ON admins(username);

-- ============================================
-- 6. 默认套餐数据
-- ============================================
INSERT OR IGNORE INTO plans (name, display_name, description, monthly_price, 
    daily_requests, daily_tokens, daily_audio_seconds,
    price_per_request, price_per_1k_tokens, price_per_minute_audio)
VALUES 
    ('free', '免费版', '基础功能，适合体验', 0, 100, 10000, 60, 0, 0, 0),
    ('basic', '基础版', '适合个人开发者', 29, 1000, 100000, 600, 0.001, 0.01, 0.1),
    ('pro', '专业版', '适合小型团队', 99, 10000, 1000000, 3600, 0.0008, 0.008, 0.08),
    ('enterprise', '企业版', '适合大型企业', 299, 100000, 10000000, 36000, 0.0005, 0.005, 0.05);
