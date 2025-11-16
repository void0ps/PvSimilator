@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo   PV Simulator 系统启动
echo ============================================================
echo.
echo [提示] 将打开两个窗口：
echo   窗口1：后端服务 (http://localhost:8000)
echo   窗口2：前端服务 (http://localhost:3000)
echo.
pause

echo.
echo [1/2] 启动后端服务...
start "PV Simulator - Backend" cmd /k "cd backend && python main.py"

echo [2/2] 等待5秒后启动前端服务...
timeout /t 5 /nobreak >nul

echo.
echo [2/2] 启动前端服务...
start "PV Simulator - Frontend" cmd /k "cd frontend\analysis && npm run dev"

echo.
echo ============================================================
echo   系统启动完成！
echo ============================================================
echo.
echo 访问地址：
echo   前端: http://localhost:3000
echo   后端: http://localhost:8000
echo   文档: http://localhost:8000/docs
echo.
echo 提示：关闭此窗口不会影响服务运行
echo       要停止服务，请关闭对应的服务窗口
echo.
pause

