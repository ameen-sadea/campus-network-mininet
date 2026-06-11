@echo off
chcp 65001 >nul
echo ============================================
echo   校园网络模拟器 v2.3 - 前端演示模式
echo ============================================
echo.

cd /d "%~dp0frontend"

echo 启动 HTTP 服务器...
echo 浏览器打开: http://localhost:8000
echo 按 Ctrl+C 停止服务器
echo.

python -m http.server 8000
