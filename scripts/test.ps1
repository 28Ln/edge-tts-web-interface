# 运行测试脚本 (Windows PowerShell)

Write-Host "Running unit tests..." -ForegroundColor Green
py -m pytest tests/unit/ -v

Write-Host "Running integration tests..." -ForegroundColor Green
py -m pytest tests/integration/ -v

# 端到端测试 (需要先启动服务器)
# Write-Host "Running e2e tests..." -ForegroundColor Green
# py -m pytest tests/e2e/ -v

Write-Host "Done!" -ForegroundColor Green
