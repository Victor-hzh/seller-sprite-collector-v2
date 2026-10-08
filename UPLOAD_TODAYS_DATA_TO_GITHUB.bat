@echo off
setlocal
chcp 65001 >nul
title SellerSprite Collector - Upload Today's 30 Files to GitHub
cd /d "%~dp0"

echo ============================================================
echo Upload Today's 30 SellerSprite Files to Independent GitHub Repo
echo ============================================================
echo.
echo Target: Victor-hzh/seller-sprite-collector-v2
echo The original amazon-bestsellers-data repository will not be used.
echo.

call "%~dp0OPEN_DATA_AND_GITHUB.bat"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
  echo Upload completed or the same data was already uploaded.
) else (
  echo Upload did not complete. Read the error above or send a screenshot to Codex.
)
pause
exit /b %EXIT_CODE%
