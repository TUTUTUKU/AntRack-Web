@echo off
chcp 65001 >nul
title AntRack 后端 - 后台静默启动
setlocal

cd /d "%~dp0backend"
if not exist "logs" mkdir logs

REM ===== 1. 防重复启动 =====
netstat -ano 2>nul | findstr /R /C:":8000 .*LISTENING" >nul
if %errorlevel%==0 (
    echo [i] 端口 8000 已经在监听（后端已启动）。
    echo     如需重启，请先运行 02_停止后端.bat。
    echo.
    pause
    exit /b 0
)

REM ===== 2. 找 Python 解释器 =====
set "PYEXE="
if exist "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\pythonw.exe" (
    set "PYEXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python311\pythonw.exe"
) else if exist "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe" (
    set "PYEXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"
)
if not defined PYEXE (
    for /f "delims=" %%i in ('where pythonw 2^>nul') do set "PYEXE=%%i" & goto :py_found
)
:py_found
if not defined PYEXE (
    for /f "delims=" %%i in ('where python 2^>nul') do set "PYEXE=%%i" & goto :py2_found
)
:py2_found
if not defined PYEXE (
    echo [x] 未找到 Python 解释器。请安装 Python 3.11 并加入 PATH。
    pause
    exit /b 1
)
echo [·] Python: %PYEXE%

REM ===== 3. 依赖检查（用 python.exe，不用 pythonw）=====
echo [·] 检查 / 同步依赖（首次慢）...
set "PY_CLI=%PYEXE:pythonw=python%"
"%PY_CLI%" -m pip install -r requirements.txt --quiet 1>nul 2>logs\pip.log
if errorlevel 1 (
    echo [x] 依赖安装失败。查看 backend\logs\pip.log
    pause
    exit /b 2
)

REM ===== 4. PowerShell Start-Process -WindowStyle Hidden 静默启动 =====
echo [·] 启动 uvicorn (0.0.0.0:8000) ...
if exist "logs\antrack.pid" del /q "logs\antrack.pid"
del /q "logs\antrack.startup_fail" 2>nul

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$p=Start-Process -FilePath '%PYEXE%' -ArgumentList '-m','uvicorn','main:app','--host','0.0.0.0','--port','8000'" ^
  " -WorkingDirectory '%~dp0backend' -WindowStyle Hidden -RedirectStandardOutput 'logs\stdout.log' -RedirectStandardError 'logs\stderr.log' -PassThru;" ^
  "$p.Id ^| Out-File -FilePath 'logs\antrack.pid' -Encoding utf8;" ^
  "Start-Sleep -Seconds 3;" ^
  "if(-not $p.HasExited){ exit 0 };" ^
  "'exit=' + $p.ExitCode ^| Out-File -FilePath 'logs\antrack.startup_fail' -Encoding utf8; exit 1"

set "ST=$?"

timeout /t 1 /nobreak >nul

if exist "logs\antrack.startup_fail" (
    echo [x] 启动失败，backend\logs\stderr.log：
    type logs\stderr.log 2>nul
    del /q "logs\antrack.startup_fail" 2>nul
    echo.
    pause
    exit /b 3
)

netstat -ano 2>nul | findstr /R /C:":8000 .*LISTENING" >nul
if %errorlevel%==0 (
    echo.
    echo [√] AntRack 后端启动成功（端口 8000 监听中）。
    echo     App / 前端填: http://本机局域网IP:8000
    echo     停止后端     : 双击 02_停止后端.bat
    echo     查看实时日志 : 双击 03_查看后端状态.bat
    echo     开机自启     : 双击 99_加入开机自启.bat
) else (
    echo [!] 端口未监听，查看 backend\logs\stderr.log：
    type logs\stderr.log 2>nul
)
echo.
timeout /t 5 >nul
endlocal
