# 重构待办清单

## ✅ 已完成 (9项)
1. 删除冗余报告文件
2. 删除调试print语句  
3. 移动uploads/tts到data目录
4. 创建logs和migrations目录
5. 删除旧的tts_old和uploads_old
6. 添加.gitkeep文件
7. 删除TASKS_ERROR_HANDLING.md
8. 删除PROJECT_ISSUES.md
9. 所有测试通过(153/153)

## 🔥 下一步 (按优先级)

### P0 - 立即处理 (1项)
- [ ] 删除ffmpeg二进制文件（已在.gitignore，需从git历史删除）

### P1 - 本周完成 (10项)

#### 代码拆分
1. [ ] 拆分 `src/api/dashboard.py` (>300行)
   - `src/api/dashboard/__init__.py`
   - `src/api/dashboard/auth.py`
   - `src/api/dashboard/users.py`
   - `src/api/dashboard/keys.py`
   - `src/api/dashboard/usage.py`

2. [ ] 拆分 `src/api/websocket.py` (>200行)
   - `src/api/websocket/__init__.py`
   - `src/api/websocket/socketio_handler.py`
   - `src/api/websocket/native_handler.py`

3. [ ] 拆分 `src/config.py` (>150行)
   - `src/config/__init__.py`
   - `src/config/server.py`
   - `src/config/services.py`

#### 架构改进
4. [ ] 创建 Repository 层
   - `src/repositories/__init__.py`
   - `src/repositories/user_repository.py`
   - `src/repositories/usage_repository.py`

5. [ ] 修复异常链 - 使用 `raise ... from e`

6. [ ] 审查 HTTP 状态码（400 vs 500）

#### 日志改进
7. [ ] 配置日志轮转
8. [ ] 生产环境JSON格式日志
9. [ ] 增强敏感信息过滤

#### 文档
10. [ ] 创建 `docs/api/error_codes.md`

### P2 - 本月完成 (10项)
11. [ ] 重组 templates 目录
12. [ ] 重组 static 目录
13. [ ] 添加 examples README
14. [ ] 为服务添加接口定义
15. [ ] 添加 Redis 缓存层
16. [ ] 补充 API 层类型注解
17. [ ] 补充工具函数类型注解
18. [ ] 添加 mypy 类型检查
19. [ ] 提升测试覆盖率到 80%
20. [ ] 添加 v1 API 废弃警告

### P3 - 按需完成 (10项)
21. [ ] 添加依赖注入
22. [ ] 添加事件系统
23. [ ] 添加性能测试
24. [ ] 添加安全扫描
25. [ ] 集成异常监控
26. [ ] 添加部署指南
27. [ ] 添加开发指南
28. [ ] 添加贡献指南
29. [ ] 使用 poetry.lock 锁定依赖
30. [ ] 添加 CI/CD 配置

## 📊 进度统计
- P0: 0/1 (0%)
- P1: 0/10 (0%)
- P2: 0/10 (0%)
- P3: 0/10 (0%)
- **总计: 9/40 完成 (22.5%)**
