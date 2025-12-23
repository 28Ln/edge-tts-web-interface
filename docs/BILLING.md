# 计费和用户管理系统

## 当前状态

### ✅ 已实现
- 用户创建和管理
- API Key 生成和撤销
- 每日配额限制 (请求数、Token、音频秒数)
- 用量记录和统计
- Dashboard 管理面板

### ❌ 待实现
- 收费计划/套餐
- 充值/支付系统
- Admin API 认证保护
- 用户自助注册
- 配额重置机制
- 账单和发票

---

## 配额系统

### 默认配额
| 配额类型 | 默认值 | 说明 |
|----------|--------|------|
| daily_requests | 1000 | 每日请求数 |
| daily_tokens | 100000 | 每日Token数 |
| daily_audio_seconds | 600 | 每日音频秒数 (10分钟) |

### 配额检查流程
```
请求 → API Key验证 → 配额检查 → 处理请求 → 记录用量
```

### 配额超限响应
```json
{
  "success": false,
  "error_code": "QUOTA_EXCEEDED",
  "message": "已达到每日requests配额上限",
  "quota": {
    "type": "requests",
    "limit": 1000,
    "remaining": 0
  }
}
```

---

## API Key 管理

### 生成方式
1. **Admin API**: `POST /admin/users` 创建用户时自动生成
2. **Admin API**: `POST /admin/users/{username}/keys` 手动创建
3. **Dashboard**: 用户详情页创建

### API Key 格式
```
etk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
- 前缀: `etk_` (Edge TTS Key)
- 随机部分: 32位十六进制

### 权限类型
| 权限 | 说明 |
|------|------|
| all | 所有权限 |
| stt | 仅语音识别 |
| tts | 仅语音合成 |
| ai | 仅AI问答 |
| voice_chat | 语音对话 |

### 认证方式
```bash
# Header方式
curl -H "X-API-Key: etk_xxx" http://localhost:3003/v2/mcu/status

# Bearer方式
curl -H "Authorization: Bearer etk_xxx" http://localhost:3003/v2/mcu/status

# Query参数方式
curl "http://localhost:3003/v2/mcu/status?api_key=etk_xxx"
```

---

## 用户管理流程

### 创建用户
```bash
curl -X POST http://localhost:3003/admin/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "daily_requests": 1000,
    "daily_tokens": 100000,
    "daily_audio_seconds": 600
  }'
```

响应:
```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com"
  },
  "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

### 查询用量
```bash
curl http://localhost:3003/admin/users/testuser
```

响应:
```json
{
  "success": true,
  "user": {...},
  "quota": {
    "daily_requests": 1000,
    "daily_tokens": 100000,
    "daily_audio_seconds": 600
  },
  "usage": {
    "date": "2025-12-23",
    "requests": {"used": 50, "limit": 1000, "remaining": 950},
    "tokens": {"used": 5000, "limit": 100000, "remaining": 95000},
    "audio_seconds": {"used": 30, "limit": 600, "remaining": 570}
  }
}
```

---

## Dashboard 管理面板

### 访问方式
```
URL: http://localhost:3003/dashboard
密码: admin123 (通过 ADMIN_PASSWORD 环境变量修改)
```

### 功能
1. **首页**: 统计概览、趋势图
2. **用户管理**: 列表、创建、编辑、启用/禁用
3. **API Key管理**: 创建、撤销
4. **用量统计**: 每日统计、用户排行

---

## 安全建议

### 生产环境必须修改
```bash
# .env
ADMIN_PASSWORD=your_strong_password
SECRET_KEY=your_random_secret_key
```

### Admin API 保护
当前 Admin API (`/admin/*`) 没有认证保护，建议:
1. 在反向代理层限制访问
2. 或添加 Admin API Key 认证

### API Key 安全
- API Key 只在创建时显示一次
- 建议定期轮换 API Key
- 不要在客户端代码中硬编码 API Key

---

## 未来计划

### 收费系统 (待实现)
```
套餐设计:
- 免费版: 100请求/天, 10000 Token/天
- 基础版: 1000请求/天, 100000 Token/天, ¥29/月
- 专业版: 10000请求/天, 1000000 Token/天, ¥99/月
- 企业版: 无限制, 按量计费
```

### 支付集成 (待实现)
- 支付宝
- 微信支付
- Stripe (国际)

### 用户自助 (待实现)
- 注册/登录
- 个人中心
- 配额购买
- 账单查看
