@echo off
chcp 65001 >nul
title AntRack 后端 - 卸载 Windows 服务
setlocal

net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [x] 需要管理员权限！右键本脚本 → 以管理员身份运行。
    pause
    exit /b 1
)

cd /d "%~dp0backend"
set "NSSM=%~dp0backend\tools\nssm\nssm.exe"

echo [·] 停止并删除服务 AntRackBackend ...
if exist "%NSSM%" (
    "%NSSM%" stop AntRackBackend >nul 2>&1
    "%NSSM%" remove AntRackBackend confirm >nul 2>&1
) else (
    sc stop AntRackBackend >nul 2>&1
    sc delete AntRackBackend >nul 2>&1
)
timeout /t 2 /nobreak >nul

REM 保险：杀 8000 进程
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /R /C:":8000 .*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

sc query AntRackBackend 2>&1 | findstr "1060" >nul
if %errorlevel%==0 (
    echo [√] AntRackBackend 服务已卸载。
) else (
    sc query AntRackBackend 2>&1
)
echo.
pause
endlocal
