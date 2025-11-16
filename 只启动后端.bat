@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo   PV Simulator - 后端服务
echo ============================================================
echo.
echo [说明] 此脚本只启动后端，不需要Node.js
echo.
echo 启动后可访问：
echo   - API: http://localhost:8000
echo   - 文档: http://localhost:8000/docs
echo.
pause

echo.
echo [1/2] 进入backend目录...
cd backend

echo [2/2] 启动后端服务...
echo       (使用系统Python环境)
echo.
echo ============================================================
echo   服务启动中...
echo   按 Ctrl+C 可停止服务
echo ============================================================
echo.

python main.py



