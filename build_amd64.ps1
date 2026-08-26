# build_amd64.ps1
# 构建 linux/amd64 镜像，导出tar，用于Ubuntu x86服务器
$ErrorActionPreference = "Continue"

Write-Host "===== 开始构建 amd64 Docker镜像 =====" -ForegroundColor Cyan

# 构建镜像；如果Dockerfile在frontend文件夹，把最后的"."改成"./frontend"
docker build --platform linux/amd64 -t antrack-web:v1.0 .

if ($LASTEXITCODE -ne 0){
    Write-Host "❌ docker build 构建失败" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "`n===== 导出镜像到tar包 =====" -ForegroundColor Cyan
docker save -o antrack-web-amd64.tar antrack-web:v1.0

if(Test-Path "antrack-web-amd64.tar"){
    Write-Host "✅ 成功！输出文件：$PWD\antrack-web-amd64.tar" -ForegroundColor Green
}else{
    Write-Host "❌ tar文件生成失败" -ForegroundColor Red
}
pause
