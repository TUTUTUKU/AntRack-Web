@echo off
chcp 65001 >nul
title AntRack 后端 - 停止
setlocal
cd /d "%~dp0backend"

REM ===== 1. 按 PID 杀进程 =====
set /p PID=<"logs\antrack.pid" 2>nul
if defined PID (
    tasklist /FI "PID eq %PID%" 2>nul | findstr /I "python" >nul
    if %errorlevel%==0 (
        echo [·] 结束后端进程 PID=%PID% ...
        taskkill /F /PID %PID% >nul 2>&1
        timeout /t 2 /nobreak >nul
    ) else (
        echo [i] PID 文件存在但对应进程已死，忽略。
    )
    del /q "logs\antrack.pid" 2>nul
)

REM ===== 2. 保险：根据端口再杀一次（防 PID 失焦）=====
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /R /C:":8000 .*LISTENING"') do (
    echo [·] 占用 8000 的 PID=%%a 强制结束 ...
    taskkill /F /PID %%a >nul 2>&1
)

timeout /t 1 /nobreak >nul

REM ===== 3. 验证 =====
netstat -ano 2>nul | findstr /R /C:":8000 .*LISTENING" >nul
if %errorlevel%==0 (
    echo [!] 8000 端口仍被占用，可能存在其他程序。
    netstat -ano | findstr /R /C:":8000 .*LISTENING"
) else (
    echo [√] AntRack 后端已停止，8000 端口已释放。
)
echo.
timeout /t 3 >nul
endlocal
