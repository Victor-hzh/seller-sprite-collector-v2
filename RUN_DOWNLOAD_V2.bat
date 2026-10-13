@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
if exist "SellerSpriteCollector.exe" (
  "SellerSpriteCollector.exe" --cli run
) else (
  ".venv\Scripts\python.exe" "collector_app.py" run
)
pause
