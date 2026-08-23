@echo off
chcp 65001 >nul
title AntRack 后端 - 安装为 Windows 服务（NSSM）
setlocal

cd /d "%~dp0backend"
if not exist "logs" mkdir logs

REM ===== 1. 管理员权限 =====
net session >nul 2>&1
if %errorlevel% NEQ 0 (
    echo [x] 需要管理员权限！右键本脚本 → 以管理员身份运行。
    pause
    exit /b 1
)

REM ===== 2. 先关一遍现有进程 =====
echo [·] 关闭已运行的实例（如有）...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /R /C:":8000 .*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM ===== 3. 找 Python =====
set "PYEXE="
if exist "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe" (
    set "PYEXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"
)
if not defined PYEXE (
    for /f "delims=" %%i in ('where python 2^>nul') do set "PYEXE=%%i" & goto :py_ok
)
:py_ok
if not defined PYEXE (
    echo [x] 未找到 Python。
    pause
    exit /b 1
)
echo [·] Python: %PYEXE%

REM ===== 4. 依赖检查 =====
echo [·] 依赖检查 ...
"%PYEXE%" -m pip install -r requirements.txt --quiet 1>nul 2>logs\pip.log
if errorlevel 1 (
    echo [x] 依赖安装失败，见 backend\logs\pip.log
    pause
    exit /b 2
)

REM ===== 5. 下载 NSSM（x64，国内镜像优先） =====
set "NSSM_DIR=%~dp0backend\tools\nssm"
set "NSSM=%NSSM_DIR%\nssm.exe"
if not exist "%NSSM%" (
    if not exist "%NSSM_DIR%" mkdir "%NSSM_DIR%" 2>nul
    echo [·] 下载 NSSM 2.24 (x64) ...
    powershell.exe -NoProfile -Command ^
      "$ProgressPreference='SilentlyContinue';" ^
      "$urls=@('https://mirrors.cloud.tencent.com/nssm/release/nssm-2.24/nssm-2.24-101-g897c7ad/nssm-2.24/win64/nssm.exe','https://nssm.cc/release/nssm-2.24-101-g897c7ad.zip','https://github.com/kirillkovalenko/nssm/raw/master/win64/nssm.exe');" ^
      "foreach($u in $urls){ try { (New-Object Net.WebClient).DownloadFile($u,'%NSSM:\=/%'); if((Test-Path '%NSSM%') -and ((Get-Item '%NSSM%').Length -gt 100000)) { break } } catch {} }"
)
if not exist "%NSSM%" (
    echo [x] NSSM 下载失败。请手动从 https://nssm.cc/download 下载 win64\nssm.exe 放到：
    echo     %NSSM_DIR%\nssm.exe
    pause
    exit /b 3
)
echo [·] NSSM: %NSSM%

REM ===== 6. 卸载旧服务（如果有）=====
"%NSSM%" stop AntRackBackend >nul 2>&1
"%NSSM%" remove AntRackBackend confirm >nul 2>&1
timeout /t 1 /nobreak >nul

REM ===== 7. 注册服务 =====
set "WD=%~dp0backend"
echo [·] 注册 Windows 服务「AntRackBackend」...
"%NSSM%" install AntRackBackend "%PYEXE%" "-m uvicorn main:app --host 0.0.0.0 --port 8000"
if errorlevel 1 (
    echo [x] nssm install 失败
    pause
    exit /b 4
)
"%NSSM%" set AntRackBackend AppDirectory "%WD%"
"%NSSM%" set AntRackBackend DisplayName "AntRack 蚁仓后端服务"
"%NSSM%" set AntRackBackend Description "Ant Rack System V1.0 后端 API（端口 8000），SQLite + FastAPI"
"%NSSM%" set AntRackDisplayName Start SERVICE_AUTO_START
REM 日志重定向
"%NSSM%" set AntRackBackend AppStdout "%WD%\logs\service_stdout.log"
"%NSSM%" set AntRackBackend AppStderr "%WD%\logs\service_stderr.log"
"%NSSM%" set AntRackBackend AppStdoutCreationDisposition 4
"%NSSM%" set AntRackBackend AppStderrCreationDisposition 4
REM 进程挂了 3 秒自动重启
"%NSSM%" set AntRackBackend AppExit Default Restart
"%NSSM%" set AntRackBackend AppRestartDelay 3000
"%NSSM%" set AntRackBackend AppNoConsole 1

REM ===== 8. 启动 =====
echo [·] 启动服务 ...
"%NSSM%" start AntRackBackend
timeout /t 5 /nobreak >nul

REM ===== 9. 验证 =====
netstat -ano 2>nul | findstr /R /C:":8000 .*LISTENING" >nul
if %errorlevel%==0 (
    echo.
    echo [√] AntRack 后端 Windows 服务安装并启动成功！
    echo     - 服务名: AntRackBackend
    echo     - 状态  : services.msc 里可查看「AntRack 蚁仓后端服务」
    echo     - 启动类型: 自动（下次开机自动启动）
    echo     - 失败重启: 崩溃后 3 秒自动拉起
    echo.
    echo     停止/卸载服务：右键管理员运行「98_卸载Windows服务.bat」
) else (
    echo [!] 端口未监听。查看 backend\logs\service_stderr.log
    type logs\service_stderr.log 2>nul
)
echo.
pause
endlocal
