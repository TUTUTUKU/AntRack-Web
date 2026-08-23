@echo off
chcp 65001 >nul
title AntRack 后端 - 加入开机自启
setlocal

REM ===== 创建「启动」文件夹里的快捷方式 → 指到 01_启动后端_后台静默.bat =====
set "SRC=%~dp001_启动后端_后台静默.bat"
set "LNK_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LNK=%LNK_DIR%\AntRackBackend.lnk"

if not exist "%SRC%" (
    echo [x] 找不到 %SRC%，请不要移动脚本位置。
    pause
    exit /b 1
)

REM ===== 用 PowerShell 创建快捷方式 =====
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$WshShell=New-Object -ComObject WScript.Shell;" ^
  "$Sc=$WshShell.CreateShortcut('%LNK%');" ^
  "$Sc.TargetPath='%SRC%';" ^
  "$Sc.WorkingDirectory='%~dp0';" ^
  "$Sc.WindowStyle=7;" ^
  "$Sc.Description='AntRack 蚁仓后端服务 - 后台静默启动';" ^
  "$Sc.Save()"

echo.
if exist "%LNK%" (
    echo [√] 已加入开机自启！
    echo     快捷方式位置: %LNK%
    echo     下次开机时会自动无窗口启动 AntRack 后端 (8000)
    echo.
    echo     若要取消开机自启：直接删除该 lnk 文件即可。
) else (
    echo [x] 快捷方式未创建成功，请手动将 01_启动后端_后台静默.bat 复制到：
    echo     开始 → 运行 → shell:startup → 回车，粘贴快捷方式。
)
echo.
pause
endlocal
