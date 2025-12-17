# API 认证和计费

## 概述

本服务支持 API Key 认证和用量计费。

## 认证方式

支持三种方式传递 API Key：

### 1. Authorization Header（推荐）

```
Authorization: Bearer sk-xxxxxxxxxxxxxxxx
```

### 2. X-API-Key Header

```
X-API-Key: sk-xxxxxxxxxxxxxxxx
```

### 3. Query Parameter

```
GET /mcu/ask?api_key=sk-xxxxxxxxxxxxxxxx
```

## 用户管理

### 创建用户

```bash
POST /admin/users
Content-Type: application/json

{
    "username": "user1",
    "email": "user1@example.com",
    "daily_requests": 1000,
    "daily_tokens": 100000,
    "daily_audio_seconds": 600
}
```

响应：
```json
{
    "success": true,
    "user": {
        "id": 1,
        "username": "user1",
        "email": "user1@example.com"
    },
    "api_key": "sk-xxxxxxxxxxxxxxxx"
}
```

> ⚠️ API Key 只在创建时返回一次，请妥善保存！

### 查询用户信息

```bash
GET /admin/users/{username}
```

### 创建新的 API Key

```bash
POST /admin/users/{username}/keys
Content-Type: application/json

{
    "name": "my-app",
    "permissions": "all"
}
```

### 查询用量

```bash
GET /admin/usage/me
Authorization: Bearer sk-xxxxxxxxxxxxxxxx
```

响应：
```json
{
    "success": true,
    "user": "user1",
    "usage": {
        "date": "2025-12-17",
        "requests": {
            "used": 100,
            "limit": 1000,
            "remaining": 900
        },
        "tokens": {
            "used": 5000,
            "limit": 100000,
            "remaining": 95000
        },
        "audio_seconds": {
            "used": 30.5,
            "limit": 600,
            "remaining": 569.5
        }
    }
}
```

## 配额说明

| 配额类型 | 默认值 | 说明 |
|---------|--------|------|
| daily_requests | 1000 | 每日请求次数 |
| daily_tokens | 100000 | 每日 AI Token 数 |
| daily_audio_seconds | 600 | 每日音频时长（秒） |

配额每日 00:00 重置。

## 错误响应

### 认证失败 (401)

```json
{
    "success": false,
    "error_code": "AUTH_FAILED",
    "message": "API Key 无效"
}
```

### 权限不足 (403)

```json
{
    "success": false,
    "error_code": "PERMISSION_DENIED",
    "message": "缺少权限: stt"
}
```

### 配额超限 (429)

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

## 权限类型

| 权限 | 说明 |
|------|------|
| all | 所有权限 |
| stt | 语音识别 |
| tts | 语音合成 |
| ai | AI 问答 |

多个权限用逗号分隔：`stt,tts`
