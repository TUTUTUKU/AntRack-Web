@echo off
chcp 65001 >nul
title AntRack 后端 - 实时状态 + 日志
setlocal
cd /d "%~dp0backend"

echo ==============================================
echo   AntRack 后端状态面板
echo ==============================================
echo.

REM ===== 1. 监听端口 =====
netstat -ano 2>nul | findstr /R /C:":8000 .*LISTENING" >nul
if %errorlevel%==0 (
    set "STATUS=运行中"
    for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /R /C:":8000 .*LISTENING"') do set "PID=%%a"
) else (
    set "STATUS=未运行"
    set "PID="
)
echo 状态    : %STATUS%
echo 进程 PID: %PID%

REM ===== 2. 本机 IP =====
echo 本机 IP :
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr "IPv4"') do echo     %%a

echo.
echo ==============================================
echo   最近 50 条访问日志 (stderr 优先)
echo ==============================================
if exist "logs\stderr.log" (
    echo --- stderr.log (最近 50 行) ---
    powershell.exe -NoProfile -Command "Get-Content 'logs\stderr.log' -Tail 50 2>$null"
)
if exist "logs\stdout.log" (
    echo.
    echo --- stdout.log (最近 50 行) ---
    powershell.exe -NoProfile -Command "Get-Content 'logs\stdout.log' -Tail 50 2>$null"
)
echo.
echo ==============================================
echo 提示: Ctrl+C 退出；日志实时刷新请再次运行本脚本。
echo ==============================================
pause
endlocal
