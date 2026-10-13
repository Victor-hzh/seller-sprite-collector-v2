@echo off
setlocal
chcp 65001 >nul
title SellerSprite Collector - Download All 30 Lists
cd /d "%~dp0"
set "PYTHONUTF8=1"

echo ============================================================
echo SellerSprite Collector - V1 Core - Download All 30 Lists
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo This patch is not inside the working V1 collector folder.
  echo Copy all patch files into your working V1 folder first.
  echo The folder must already contain collector.py and .venv.
  echo.
  pause
  exit /b 1
)

if not exist "collector.py" (
  echo collector.py was not found in this folder.
  echo Copy this patch into the working V1 collector folder.
  pause
  exit /b 1
)

echo [1/2] Checking SellerSprite login status...
".venv\Scripts\python.exe" "seller_sprite_auto_login.py" --config "config_all_30.json"
if errorlevel 1 (
  echo.
  echo SellerSprite login was not completed.
  echo Run SAVE_LOGIN_ON_THIS_PC.bat again or send a screenshot to Codex.
  pause
  exit /b 1
)

echo.
echo [2/2] Starting 30 downloads with the original V1 browser workflow...
echo Completed tasks from today will be skipped automatically.
echo If interrupted, run this file again to continue unfinished tasks.
echo Keep Chrome and this command window open.
echo.
".venv\Scripts\python.exe" "collector_icon_export.py" run --config "config_all_30.json"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo Process exited with code %EXIT_CODE%.
if "%EXIT_CODE%"=="0" (
  echo All 30 download tasks completed.
  echo Excel files are in data\source\DATE.
) else (
  echo Some tasks did not finish.
  echo Run this file again to retry unfinished tasks.
  echo Diagnostics are in runtime\errors.
)
pause
exit /b %EXIT_CODE%

