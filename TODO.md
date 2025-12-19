# 待办事项

## ✅ 已完成
- [x] 删除冗余报告文件
- [x] 删除调试print语句
- [x] 移动uploads和tts到data目录
- [x] 创建logs和migrations目录

## 🔥 下一步（按优先级）

### 1. 删除ffmpeg二进制文件
```bash
# 从版本控制中删除
git rm -r ffmpeg/
# 更新文档说明需要系统安装ffmpeg
```

### 2. 拆分dashboard.py (>300行)
- 创建 `src/api/dashboard/__init__.py`
- 创建 `src/api/dashboard/auth.py` - 登录相关
- 创建 `src/api/dashboard/users.py` - 用户管理
- 创建 `src/api/dashboard/keys.py` - API Key管理
- 创建 `src/api/dashboard/usage.py` - 用量统计

### 3. 拆分websocket.py (>200行)
- 创建 `src/api/websocket/__init__.py`
- 创建 `src/api/websocket/socketio_handler.py`
- 创建 `src/api/websocket/native_handler.py`

### 4. 创建Repository层
- 创建 `src/repositories/__init__.py`
- 创建 `src/repositories/user_repository.py`
- 创建 `src/repositories/usage_repository.py`

### 5. 异常链修复
- 搜索所有 `raise` 语句
- 改为 `raise ... from e`

### 6. 日志配置
- 配置日志轮转
- 生产环境JSON格式
- 增强敏感信息过滤

### 7. 文档
- 创建 `docs/api/error_codes.md`
- 更新 README 说明ffmpeg安装
- 添加迁移指南

## 📊 进度
- P0任务: 7/9 完成 (78%)
- P1任务: 2/20 完成 (10%)
- 总体: 9/50 完成 (18%)
