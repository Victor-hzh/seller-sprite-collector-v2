Unicode True
!include "MUI2.nsh"

!ifndef PROJECT_ROOT
  !error "Pass /DPROJECT_ROOT=<repository path> to makensis"
!endif

Name "SellerSprite Collector V2"
OutFile "${PROJECT_ROOT}\dist\SellerSpriteCollector-v2-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\SellerSpriteCollector"
RequestExecutionLevel user
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\SellerSpriteCollector.exe"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

Section "SellerSprite Collector" SEC_MAIN
  SetOutPath "$INSTDIR"
  File "${PROJECT_ROOT}\dist\SellerSpriteCollector-v2\SellerSpriteCollector.exe"
  File "${PROJECT_ROOT}\dist\SellerSpriteCollector-v2\config_v2.json"
  File "${PROJECT_ROOT}\dist\SellerSpriteCollector-v2\tasks_v2.json"
  File "${PROJECT_ROOT}\dist\SellerSpriteCollector-v2\save_login_credentials.ps1"
  File "${PROJECT_ROOT}\dist\SellerSpriteCollector-v2\save_github_token.ps1"
  File "${PROJECT_ROOT}\dist\SellerSpriteCollector-v2\decrypt_login_password.ps1"
  File "${PROJECT_ROOT}\dist\SellerSpriteCollector-v2\README_WINDOWS_GUI.txt"
  SetOutPath "$INSTDIR\cleaning"
  File "${PROJECT_ROOT}\dist\SellerSpriteCollector-v2\cleaning\cleaning_rules.json"
  File "${PROJECT_ROOT}\dist\SellerSpriteCollector-v2\cleaning\exchange_rates.json"
  CreateDirectory "$INSTDIR\data\source"
  CreateDirectory "$INSTDIR\runtime"
  CreateShortCut "$SMPROGRAMS\SellerSprite Collector V2.lnk" "$INSTDIR\SellerSpriteCollector.exe"
  CreateShortCut "$DESKTOP\SellerSprite Collector V2.lnk" "$INSTDIR\SellerSpriteCollector.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SellerSpriteCollectorV2" "DisplayName" "SellerSprite Collector V2"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SellerSpriteCollectorV2" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SellerSpriteCollectorV2" "DisplayIcon" "$INSTDIR\SellerSpriteCollector.exe"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SellerSpriteCollectorV2" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SellerSpriteCollectorV2" "NoRepair" 1
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\SellerSprite Collector V2.lnk"
  Delete "$DESKTOP\SellerSprite Collector V2.lnk"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SellerSpriteCollectorV2"
  Delete "$INSTDIR\SellerSpriteCollector.exe"
  Delete "$INSTDIR\config_v2.json"
  Delete "$INSTDIR\tasks_v2.json"
  Delete "$INSTDIR\save_login_credentials.ps1"
  Delete "$INSTDIR\save_github_token.ps1"
  Delete "$INSTDIR\decrypt_login_password.ps1"
  Delete "$INSTDIR\README_WINDOWS_GUI.txt"
  Delete "$INSTDIR\cleaning\cleaning_rules.json"
  Delete "$INSTDIR\cleaning\exchange_rates.json"
  RMDir "$INSTDIR\cleaning"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  ; Keep runtime login state and downloaded Excel files for the user.
SectionEnd
