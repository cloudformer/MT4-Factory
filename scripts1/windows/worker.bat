@echo off
chcp 65001 >nul
title Windows MT5 Worker 管理

:MENU
cls
echo.
echo ==========================================
echo   Windows MT5 Worker 管理菜单
echo ==========================================
echo.
echo   1. 安装MT5终端
echo   2. 下载历史数据
echo   3. 启动Bridge监听
echo   4. 查看状态
echo   0. 退出
echo.
echo ==========================================
echo.

set /p choice="请选择操作 [0-4]: "

if "%choice%"=="1" goto INSTALL_MT5
if "%choice%"=="2" goto DOWNLOAD_DATA
if "%choice%"=="3" goto START_BRIDGE
if "%choice%"=="4" goto CHECK_STATUS
if "%choice%"=="0" goto EXIT
goto MENU

REM ==========================================
REM 1. 安装MT5终端
REM ==========================================
:INSTALL_MT5
cls
echo.
echo [1] 安装MT5终端
echo ==========================================
echo.
echo MT5官方下载地址:
echo   https://www.metatrader5.com/en/download
echo.
echo 安装步骤:
echo   1. 下载MT5安装程序
echo   2. 运行安装（默认路径即可）
echo   3. 启动MT5并登录账户
echo   4. 确保MT5保持运行状态
echo.
echo 按任意键打开下载页面...
pause >nul
start https://www.metatrader5.com/en/download
echo.
echo MT5安装完成后，返回此菜单选择其他操作
echo.
pause
goto MENU

REM ==========================================
REM 2. 下载历史数据
REM ==========================================
:DOWNLOAD_DATA
cls
echo.
echo [2] 下载历史数据
echo ==========================================
echo.

REM 检查MT5 Bridge是否运行
curl -s http://localhost:9090/health >nul 2>&1
if errorlevel 1 (
    echo [X] MT5 Bridge未运行！
    echo     请先选择"3. 启动Bridge监听"
    echo.
    pause
    goto MENU
)

echo 请选择下载天数:
echo   1. 7天（默认）
echo   2. 30天
echo   3. 自定义
echo.
set /p days_choice="请选择 [1-3]: "

set DAYS=7
if "%days_choice%"=="2" set DAYS=30
if "%days_choice%"=="3" (
    set /p DAYS="请输入天数: "
)

echo.
echo [→] 开始下载最近 %DAYS% 天的历史数据...
echo.

set DEVICE=windows
set PYTHONPATH=%cd%
python scripts\tools\update_historical_data.py --days %DAYS%

echo.
echo [✓] 下载完成
echo.
pause
goto MENU

REM ==========================================
REM 3. 启动Bridge监听
REM ==========================================
:START_BRIDGE
cls
echo.
echo [3] 启动Bridge监听
echo ==========================================
echo.

REM 检查MT5终端是否运行
tasklist /FI "IMAGENAME eq terminal64.exe" 2>nul | find /I "terminal64.exe">nul
if errorlevel 1 (
    tasklist /FI "IMAGENAME eq terminal.exe" 2>nul | find /I "terminal.exe">nul
    if errorlevel 1 (
        echo [X] MT5终端未运行！
        echo.
        echo 请先启动MetaTrader5并登录账户
        echo 然后重新选择此选项
        echo.
        pause
        goto MENU
    )
)

echo [✓] MT5终端已运行
echo.

REM 检查是否已经在运行
curl -s http://localhost:9090/health >nul 2>&1
if not errorlevel 1 (
    echo [!] Bridge已在运行中
    echo.
    pause
    goto MENU
)

echo [→] 启动MT5 Bridge...
echo.
echo 监听地址: http://0.0.0.0:9090
echo API文档:  http://localhost:9090/docs
echo.
echo 按 Ctrl+C 停止服务
echo.

set DEVICE=windows
set PYTHONPATH=%cd%
python -m uvicorn src.services.mt5_api_bridge.app:app --host 0.0.0.0 --port 9090

pause
goto MENU

REM ==========================================
REM 4. 查看状态
REM ==========================================
:CHECK_STATUS
cls
echo.
echo [4] 查看状态
echo ==========================================
echo.

REM 检查MT5终端
echo [MT5终端]
tasklist /FI "IMAGENAME eq terminal64.exe" 2>nul | find /I "terminal64.exe">nul
if errorlevel 1 (
    tasklist /FI "IMAGENAME eq terminal.exe" 2>nul | find /I "terminal.exe">nul
    if errorlevel 1 (
        echo   状态: ❌ 未运行
    ) else (
        echo   状态: ✅ 运行中 (terminal.exe)
    )
) else (
    echo   状态: ✅ 运行中 (terminal64.exe)
)
echo.

REM 检查MT5 Bridge
echo [MT5 Bridge]
curl -s http://localhost:9090/health >nul 2>&1
if errorlevel 1 (
    echo   状态: ❌ 未运行
    echo   端口: 9090
) else (
    echo   状态: ✅ 运行中
    echo   端口: 9090
    echo   API:  http://localhost:9090/docs

    REM 获取账户信息
    echo.
    echo [账户信息]
    curl -s http://localhost:9090/account/info 2>nul | python -c "import sys, json; d=json.load(sys.stdin); print(f'   账号: {d.get(\"login\")}'); print(f'   服务器: {d.get(\"server\")}'); print(f'   余额: {d.get(\"balance\")}')" 2>nul
)
echo.

REM 网络信息
echo [网络信息]
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set ip=%%a
    set ip=!ip:~1!
    echo   IP地址: !ip!
    goto :IP_DONE
)
:IP_DONE
echo   端口: 9090
echo.

echo ==========================================
echo.
pause
goto MENU

REM ==========================================
REM 0. 退出
REM ==========================================
:EXIT
echo.
echo 再见！
timeout /t 1 /nobreak >nul
exit
