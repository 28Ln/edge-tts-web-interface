#!/bin/bash
# 运行测试脚本

# 单元测试
echo "Running unit tests..."
python -m pytest tests/unit/ -v

# 集成测试
echo "Running integration tests..."
python -m pytest tests/integration/ -v

# 端到端测试 (需要先启动服务器)
# echo "Running e2e tests..."
# python -m pytest tests/e2e/ -v

echo "Done!"
