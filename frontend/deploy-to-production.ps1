# 光伏仿真系统前端部署脚本（PowerShell版本）

Write-Host "========================================" -ForegroundColor Green
Write-Host "光伏仿真系统前端部署脚本" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# 设置变量
$Server = "ubuntu@129.204.185.217"
$WebRoot = "/var/www/html/pv-simulator"
$KeyFile = "F:\Download\cjj.pem"

# 检查密钥文件是否存在
if (-not (Test-Path $KeyFile)) {
    Write-Host "错误：密钥文件不存在：$KeyFile" -ForegroundColor Red
    Write-Host "请修改脚本中的KeyFile路径" -ForegroundColor Yellow
    Read-Host "按任意键退出"
    exit 1
}

Write-Host "1. 构建前端应用..." -ForegroundColor Cyan
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "错误：构建失败！" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

Write-Host ""
Write-Host "2. 复制文件到生产服务器..." -ForegroundColor Cyan
$scpCommand = "scp -r -i `"$KeyFile`" dist/* $Server`:$WebRoot/"
Invoke-Expression $scpCommand

if ($LASTEXITCODE -ne 0) {
    Write-Host "错误：文件复制失败！" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

Write-Host ""
Write-Host "3. 设置文件权限..." -ForegroundColor Cyan
$sshCommand = "ssh -i `"$KeyFile`" $Server `"sudo chmod -R 755 $WebRoot && sudo chown -R www-data:www-data $WebRoot`""
Invoke-Expression $sshCommand

if ($LASTEXITCODE -ne 0) {
    Write-Host "错误：权限设置失败！" -ForegroundColor Red
    Read-Host "按任意键退出"
    exit 1
}

Write-Host ""
Write-Host "4. 重启Web服务..." -ForegroundColor Cyan
$sshCommand = "ssh -i `"$KeyFile`" $Server `"sudo systemctl restart nginx`""
Invoke-Expression $sshCommand

if ($LASTEXITCODE -ne 0) {
    Write-Host "警告：Web服务重启失败，但部署已完成" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "部署完成！" -ForegroundColor Green
Write-Host "访问地址：http://129.204.185.217/analysis" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Read-Host "按任意键退出"