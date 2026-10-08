@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONUTF8=1"
if exist "SellerSpriteCollector.exe" (
  "SellerSpriteCollector.exe" run
) else (
  ".venv\Scripts\python.exe" "collector_icon_export.py" run --config "config_v2.json"
)
pause
