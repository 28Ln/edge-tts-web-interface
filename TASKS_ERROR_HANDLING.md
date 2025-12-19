# 异常处理和日志完善任务清单

## 🔴 高优先级

### 1. API 层统一异常处理
- [x] `src/api/v1/mcu.py` - 所有接口添加 try-catch，统一返回格式 ✅
- [x] `src/api/v1/wechat.py` - 所有接口添加 try-catch ✅
- [x] `src/api/v2/mcu.py` - 所有接口添加 try-catch ✅
- [x] `src/api/admin.py` - 所有接口添加 try-catch ✅
- [x] `src/api/dashboard.py` - 所有接口添加 try-catch ✅

### 2. 服务层异常细化
- [x] `src/services/ai_service.py` - 区分网络错误、API错误、超时错误 ✅
- [x] `src/services/tts_service.py` - 区分 edge-tts 错误、ffmpeg 错误 ✅
- [x] `src/services/asr_service.py` - 区分引擎错误、音频格式错误、网络错误 ✅
- [ ] `src/services/asr/tencent.py` - 添加腾讯云特定错误处理

### 3. 日志增强
- [x] 所有 API 接口添加请求参数日志 ✅
- [x] 所有服务调用添加耗时日志 ✅
- [x] 所有错误添加堆栈跟踪（开发环境）✅
- [ ] 添加用户操作审计日志

## 🟡 中优先级

### 4. 输入验证增强
- [x] `src/api/v1/mcu.py` - 验证音频大小、格式 ✅
- [x] `src/api/v1/wechat.py` - 验证消息长度、格式 ✅
- [x] `src/api/v2/mcu.py` - 验证所有输入参数 ✅
- [x] `src/api/admin.py` - 验证用户名、邮箱格式 ✅

### 5. 超时处理
- [x] AI 服务调用添加超时（30秒）✅
- [x] ASR 服务调用添加超时（60秒）✅
- [x] TTS 服务调用添加超时（30秒）✅
- [ ] 数据库操作添加超时

### 6. 重试机制
- [x] AI 服务失败自动重试（3次）✅
- [ ] 腾讯云 ASR 失败自动重试（2次）- 配置已添加
- [ ] TTS 服务失败自动重试（2次）- 配置已添加

## 🟢 低优先级

### 7. 错误恢复
- [ ] AI 服务降级（使用缓存响应）
- [ ] ASR 服务降级（Vosk → 腾讯云 → 返回错误）
- [ ] TTS 服务降级（edge-tts 失败时的备选方案）

### 8. 监控告警
- [ ] 错误率监控（每分钟错误数）
- [ ] 响应时间监控（P95、P99）
- [ ] 服务可用性监控
- [ ] 配额使用监控

### 9. 日志优化
- [ ] 敏感信息脱敏（API Key、密码）
- [ ] 日志分级（DEBUG/INFO/WARNING/ERROR）
- [ ] 日志轮转（按天、按大小）
- [ ] 结构化日志（JSON 格式）

## 📋 具体任务

### Task 1: MCU API v1 异常处理 ✅
**文件**: `src/api/v1/mcu.py`

```python
# 已完成的修改
✅ stt()          # 添加音频大小验证、格式验证、耗时日志
✅ ask()          # 添加问题长度验证、JSON 错误处理、耗时日志
- ask_stream()   # 添加流式错误处理（已有基础处理）
✅ tts()          # 添加文本长度验证、格式验证、耗时日志
✅ voice_chat()   # 添加完整错误处理链、分段耗时日志
```

### Task 2: 微信 API 异常处理
**文件**: `src/api/v1/wechat.py`

```python
# 需要修改的接口
- wechat_callback()  # 添加 XML 解析错误处理
- wechat_chat()      # ✅ 已完成 JSON 错误处理
- wechat_voice()     # 添加音频处理错误
- wechat_stt()       # 添加格式转换错误
```

### Task 3: AI 服务异常细化
**文件**: `src/services/ai_service.py`

```python
# 需要添加的异常类型
- AIConnectionError    # 网络连接错误
- AITimeoutError       # 超时错误
- AIRateLimitError     # 速率限制错误
- AIInvalidKeyError    # API Key 无效
- AIModelError         # 模型错误
```

### Task 4: ASR 服务异常细化
**文件**: `src/services/asr_service.py`

```python
# 需要添加的异常类型
- ASREngineNotAvailable  # 引擎不可用
- ASRFormatError         # 音频格式错误
- ASRTimeoutError        # 识别超时
- ASRNetworkError        # 网络错误
```

### Task 5: 日志增强
**所有文件**

```python
# 需要添加的日志
- 请求开始: logger.info(f"[API] 开始处理 | endpoint={} | params={}")
- 请求结束: logger.info(f"[API] 处理完成 | endpoint={} | duration={}ms")
- 服务调用: logger.debug(f"[Service] 调用 | service={} | params={}")
- 错误详情: logger.error(f"[Error] 错误 | type={} | message={} | trace={}")
```

### Task 6: 输入验证
**所有 API 文件**

```python
# 需要添加的验证
- 音频大小: max 10MB
- 文本长度: max 5000 字符
- 问题长度: max 1000 字符
- 文件格式: 白名单验证
- 参数范围: 数值范围检查
```

### Task 7: 超时配置
**配置文件**: `src/config.py`

```python
# 需要添加的配置
AI_TIMEOUT = 30          # AI 服务超时（秒）
ASR_TIMEOUT = 60         # ASR 服务超时（秒）
TTS_TIMEOUT = 30         # TTS 服务超时（秒）
DB_TIMEOUT = 5           # 数据库超时（秒）
```

### Task 8: 重试配置
**工具文件**: `src/utils/retry.py`

```python
# 需要配置的重试策略
- AI 服务: 3次，指数退避
- ASR 服务: 2次，固定间隔
- TTS 服务: 2次，固定间隔
- 网络请求: 3次，指数退避
```

## 🎯 实施顺序

### 第一阶段（1-2天）
1. ✅ Task 1: MCU API v1 异常处理
2. ✅ Task 2: 微信 API 异常处理（部分完成：chat, voice）
3. Task 5: 基础日志增强（进行中）

### 第二阶段（1-2天）
4. Task 3: AI 服务异常细化
5. Task 4: ASR 服务异常细化
6. Task 6: 输入验证

### 第三阶段（1天）
7. Task 7: 超时配置
8. Task 8: 重试机制

### 第四阶段（可选）
9. 错误恢复和降级
10. 监控告警
11. 日志优化

## 📝 代码模板

### 异常处理模板
```python
@route('/api/endpoint', methods=['POST'])
def endpoint():
    try:
        # 1. 参数验证
        data = validate_input(request)
        
        # 2. 业务逻辑
        logger.info(f"[API] 开始处理 | endpoint=/api/endpoint")
        start_time = time.time()
        
        result = service.process(data)
        
        duration = (time.time() - start_time) * 1000
        logger.info(f"[API] 处理完成 | duration={duration:.2f}ms")
        
        # 3. 返回结果
        return jsonify(make_response(result))
        
    except ValidationError as e:
        logger.warning(f"[API] 验证失败 | error={e}")
        return jsonify(make_error('VALIDATION_ERROR', str(e))), 400
        
    except ServiceError as e:
        logger.error(f"[API] 服务错误 | error={e}")
        return jsonify(make_error('SERVICE_ERROR', str(e))), 500
        
    except Exception as e:
        logger.error(f"[API] 未知错误 | error={e}", exc_info=True)
        return jsonify(make_error('INTERNAL_ERROR', '服务器内部错误')), 500
```

### 日志模板
```python
# 请求日志
logger.info(f"[{module}] 请求 | method={method} | params={params}")

# 处理日志
logger.debug(f"[{module}] 处理中 | step={step} | data={data}")

# 成功日志
logger.info(f"[{module}] 成功 | result={result} | duration={duration}ms")

# 错误日志
logger.error(f"[{module}] 失败 | error={error} | trace={trace}")
```

### 验证模板
```python
def validate_audio(audio_data):
    """验证音频数据"""
    if not audio_data:
        raise ValidationError("音频数据为空")
    
    if len(audio_data) > 10 * 1024 * 1024:  # 10MB
        raise ValidationError("音频文件过大，最大 10MB")
    
    return audio_data

def validate_text(text, max_length=5000):
    """验证文本"""
    if not text or not text.strip():
        raise ValidationError("文本内容为空")
    
    if len(text) > max_length:
        raise ValidationError(f"文本过长，最大 {max_length} 字符")
    
    return text.strip()
```

## ✅ 完成标准

每个任务完成后需要：
1. ✅ 代码实现
2. ✅ 添加单元测试
3. ✅ 更新文档
4. ✅ 本地测试通过
5. ✅ 代码审查通过
