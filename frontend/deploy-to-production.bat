@echo off
echo ========================================
echo 光伏仿真系统前端部署脚本
echo ========================================

REM 设置变量
set SERVER=ubuntu@129.204.185.217
set WEB_ROOT=/var/www/html/pv-simulator
set KEY_FILE=F:\Download\cjj.pem

REM 检查密钥文件是否存在
if not exist "%KEY_FILE%" (
    echo 错误：密钥文件不存在：%KEY_FILE%
    echo 请修改脚本中的KEY_FILE路径
    pause
    exit /b 1
)

echo 1. 构建前端应用...
npm run build

if %errorlevel% neq 0 (
    echo 错误：构建失败！
    pause
    exit /b 1
)

echo.
echo 2. 复制文件到生产服务器...
scp -r -i "%KEY_FILE%" dist/* %SERVER%:%WEB_ROOT/

if %errorlevel% neq 0 (
    echo 错误：文件复制失败！
    pause
    exit /b 1
)

echo.
echo 3. 设置文件权限...
ssh -i "%KEY_FILE%" %SERVER% "sudo chmod -R 755 %WEB_ROOT% && sudo chown -R www-data:www-data %WEB_ROOT%"

if %errorlevel% neq 0 (
    echo 错误：权限设置失败！
    pause
    exit /b 1
)

echo.
echo 4. 重启Web服务...
ssh -i "%KEY_FILE%" %SERVER% "sudo systemctl restart nginx"

if %errorlevel% neq 0 (
    echo 警告：Web服务重启失败，但部署已完成
)

echo.
echo ========================================
echo 部署完成！
echo 访问地址：http://129.204.185.217/analysis
echo ========================================

pause