@echo off
REM ESP32-S3 EdgeTTS Client 编译脚本

echo ========================================
echo   ESP32-S3 EdgeTTS Client 编译脚本
echo ========================================
echo.

REM 检查是否设置了IDF环境
if not defined IDF_PATH (
    echo 错误: 未找到ESP-IDF环境
    echo 请先运行: C:\Espressif\frameworks\esp-idf-v5.2.2\export.bat
    pause
    exit /b 1
)

echo IDF_PATH: %IDF_PATH%
echo.

REM 选择操作
echo 请选择操作:
echo 1. 配置项目 (menuconfig)
echo 2. 清理项目 (fullclean)
echo 3. 编译项目 (build)
echo 4. 清理并编译 (fullclean + build)
echo 5. 退出
echo.

set /p choice="请输入选项 (1-5): "

if "%choice%"=="1" (
    echo.
    echo 正在打开配置菜单...
    idf.py menuconfig
) else if "%choice%"=="2" (
    echo.
    echo 正在清理项目...
    idf.py fullclean
    echo 清理完成!
) else if "%choice%"=="3" (
    echo.
    echo 正在编译项目...
    idf.py build
    if %errorlevel% equ 0 (
        echo.
        echo ========================================
        echo   编译成功!
        echo ========================================
    ) else (
        echo.
        echo ========================================
        echo   编译失败!
        echo ========================================
    )
) else if "%choice%"=="4" (
    echo.
    echo 正在清理项目...
    idf.py fullclean
    echo.
    echo 正在编译项目...
    idf.py build
    if %errorlevel% equ 0 (
        echo.
        echo ========================================
        echo   编译成功!
        echo ========================================
    ) else (
        echo.
        echo ========================================
        echo   编译失败!
        echo ========================================
    )
) else if "%choice%"=="5" (
    exit /b 0
) else (
    echo 无效的选项!
)

echo.
pause
