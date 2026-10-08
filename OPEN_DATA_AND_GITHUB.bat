@echo off
setlocal
chcp 65001 >nul
title SellerSprite Collector - Open Data and GitHub
cd /d "%~dp0"

for /f %%D in ('powershell.exe -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set "RUN_DATE=%%D"
set "DATA_FOLDER=%~dp0data\source\%RUN_DATE%"
set "GITHUB_UPLOAD_URL=https://github.com/Victor-hzh/seller-sprite-collector-v2/upload/main/data/source/%RUN_DATE%"

echo ============================================================
echo Open Today's Data Folder and GitHub Upload Page
echo ============================================================
echo.

if not exist "%DATA_FOLDER%" (
  echo Today's data folder was not found:
  echo %DATA_FOLDER%
  echo.
  echo Opening the main data folder instead.
  set "DATA_FOLDER=%~dp0data\source"
)

start "" explorer.exe "%DATA_FOLDER%"
start "" "%GITHUB_UPLOAD_URL%"

echo Two windows are opening now:
echo 1. In the data folder, press Ctrl+A to select the 30 files.
echo 2. Drag them into the GitHub upload page.
echo 3. On GitHub, scroll down and click Commit changes.
echo.
echo Target repository: Victor-hzh/seller-sprite-collector-v2
echo The original repository is not used.
echo.
pause
exit /b 0
