# 重构清单 - 为大型项目做准备

## 🔴 紧急 (P0) - 立即处理

### 目录结构
- [ ] 删除根目录的 `app.py`（已有 `src/main.py`）
- [ ] 移动 `uploads/` 到 `data/uploads/`
- [ ] 移动 `tts/` 到 `data/tts/`
- [ ] 删除 `ffmpeg/` 二进制文件（通过系统安装）
- [ ] 删除所有 `OPTIMIZATION_*.md` 报告文件

### 文件命名
- [ ] 统一测试文件命名：`test_<module>_<feature>.py`
- [ ] 删除 `test_error_handling.py`（临时测试文件）

### 代码清理
- [ ] 删除所有 `print()` 调试语句
- [ ] 删除 `__pycache__` 目录（添加到 .gitignore）

## 🟠 高优先级 (P1) - 本周完成

### 目录结构
- [ ] 创建 `data/logs/` 目录
- [ ] 创建 `migrations/` 数据库迁移目录
- [ ] 重组 `templates/`: `templates/web/`, `templates/dashboard/`
- [ ] 重组 `static/`: `static/assets/css/`, `static/assets/js/`, `static/assets/img/`
- [ ] 每个 `examples/` 子目录添加 README.md

### 代码架构
- [ ] 拆分 `dashboard.py` (>300行) → `dashboard/routes.py`, `dashboard/views.py`
- [ ] 拆分 `websocket.py` (>200行) → `websocket/socketio.py`, `websocket/native.py`
- [ ] 创建 `src/repositories/` 数据访问层
- [ ] 拆分 `config.py` (>150行) → 多个配置类

### 异常架构
- [ ] 使用 `raise ... from e` 保留异常链
- [ ] 审查所有 HTTP 状态码（400 vs 500）
- [ ] 创建 `docs/api/error_codes.md` 错误码文档

### 日志架构
- [ ] 配置日志轮转（按天/按大小）
- [ ] 生产环境使用 JSON 格式日志
- [ ] 增强敏感信息过滤（密码、token等）
- [ ] 添加审计日志表

## 🟡 中优先级 (P2) - 本月完成

### 目录结构
- [ ] 移动 `README.en.md` 到 `docs/`
- [ ] 统一 `docs/api/` 文档格式
- [ ] 添加 `scripts/setup.sh`, `scripts/deploy.sh`, `scripts/backup.sh`

### 代码架构
- [ ] 为 AIService, TTSService 添加接口定义
- [ ] 添加事件系统（事件总线）
- [ ] 添加 Redis 缓存层
- [ ] 使用 Flask 应用上下文替代全局变量

### 代码质量
- [ ] 补充所有公开函数的 docstring
- [ ] 拆分超过 50 行的函数
- [ ] 添加 `pyproject.toml` 中 black/ruff 配置
- [ ] 添加 flake8/ruff lint 配置
- [ ] 添加 bandit 安全检查
- [ ] 提高测试覆盖率到 80%

### 兼容性
- [ ] 制定 v1 API 废弃时间表
- [ ] 添加 v1 API 废弃警告
- [ ] 文档说明 `GEMINI_*` → `AI_*` 迁移
- [ ] 使用 `poetry.lock` 或 `pip-tools` 锁定依赖
- [ ] 添加 `X-API-Version` 响应头

## 🟢 低优先级 (P3) - 按需完成

### 目录结构
- [ ] 考虑使用 `static/assets/` 统一管理
- [ ] 添加 `.env.development`, `.env.production` 示例

### 代码架构
- [ ] 考虑使用 Flask-Injector 依赖注入
- [ ] 添加性能测试（locust）
- [ ] 集成异常监控（Sentry）

### 文档
- [ ] 添加部署指南
- [ ] 添加开发指南
- [ ] 添加贡献指南

---

## 📋 具体问题清单 (50项)

### 一、目录结构 (10项)
1. 根目录有 `app.py` 和 `src/main.py` 双入口
2. `uploads/`, `tts/` 在根目录，应该在 `data/`
3. `ffmpeg/` 包含 Windows 二进制，不应纳入版本控制
4. `static/` 目录结构混乱（css/js/img 分散）
5. `templates/` 层级不清晰（index.html 和 dashboard/ 混合）
6. 缺少 `logs/` 目录
7. `data/` 目录结构不完整
8. `scripts/` 目录不完整（只有测试脚本）
9. 缺少 `migrations/` 数据库迁移目录
10. `examples/` 缺少统一 README

### 二、文件命名 (5项)
11. 测试文件命名不一致（`test_api_mcu.py` vs `test_admin_api.py`）
12. `README.md` 和 `README.en.md` 在根目录
13. 服务文件命名不一致（`ai_service.py` vs `session_store.py`）
14. 临时测试文件 `test_error_handling.py` 未删除
15. 报告文件过多（`OPTIMIZATION_*.md`）

### 三、代码架构 (10项)
16. `dashboard.py` 超过 300 行
17. `websocket.py` 超过 200 行
18. 缺少 Repository 数据访问层
19. 直接在路由中操作数据库
20. 服务层缺少接口定义（只有 ASREngine 有）
21. 缺少事件系统
22. 缺少缓存层
23. `config.py` 超过 150 行
24. 使用模块级全局变量
25. 缺少依赖注入

### 四、日志架构 (5项)
26. 日志级别使用不当（部分 INFO 应该是 DEBUG）
27. 缺少结构化日志（生产环境应该用 JSON）
28. 缺少审计日志
29. 日志轮转未配置
30. 敏感信息过滤不完整（只过滤 API Key）

### 五、异常架构 (5项)
31. 异常链丢失（未使用 `raise ... from e`）
32. 缺少错误码文档
33. HTTP 状态码使用不一致
34. 缺少异常监控集成
35. 部分异常未保留原始异常

### 六、代码质量 (10项)
36. 类型注解不完整（API 层、工具函数）
37. 文档字符串不完整
38. 部分函数超过 50 行
39. 存在调试 `print()` 语句
40. 缺少代码格式化工具配置
41. 缺少 lint 检查配置
42. 测试覆盖率 70%（目标 80%）
43. 缺少性能测试
44. 缺少安全扫描
45. `__pycache__` 未添加到 .gitignore

### 七、兼容性 (5项)
46. v1/v2 API 并存无迁移计划
47. `GEMINI_*` 和 `AI_*` 环境变量并存
48. 依赖版本过于宽松（无版本锁定）
49. 缺少 API 版本头
50. 缺少废弃警告机制

---

## 🎯 执行顺序

### 第一步：清理（今天）
1. 删除冗余文件和报告
2. 删除调试代码
3. 更新 .gitignore

### 第二步：重组目录（明天）
1. 移动文件到正确位置
2. 创建缺失目录
3. 重命名不规范文件

### 第三步：代码重构（本周）
1. 拆分过长文件
2. 添加 Repository 层
3. 完善类型注解

### 第四步：架构优化（本月）
1. 添加缓存层
2. 完善日志系统
3. 提升测试覆盖率
