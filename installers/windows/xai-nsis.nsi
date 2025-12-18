; NSIS Script for XAI Blockchain
; Alternative to Inno Setup - builds Windows installer
; Requires NSIS 3.08+ from https://nsis.sourceforge.io/

!define PRODUCT_NAME "XAI Blockchain"
!define PRODUCT_VERSION "0.2.0"
!define PRODUCT_PUBLISHER "XAI Blockchain Team"
!define PRODUCT_WEB_SITE "https://xai-blockchain.io"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\xai-node.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"
!define PYTHON_VERSION "3.12.1"

; Includes
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "xai.ico"
!define MUI_UNICON "xai.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "sidebar.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "header.bmp"
!define MUI_FINISHPAGE_RUN "$INSTDIR\xai-node.bat"
!define MUI_FINISHPAGE_RUN_TEXT "Start XAI Node"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\docs\README.md"

; Welcome page
!insertmacro MUI_PAGE_WELCOME
; License page
!insertmacro MUI_PAGE_LICENSE "..\..\LICENSE"
; Components page
!insertmacro MUI_PAGE_COMPONENTS
; Directory page
!insertmacro MUI_PAGE_DIRECTORY
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES

; Language files
!insertmacro MUI_LANGUAGE "English"

; General
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "output\xai-blockchain-${PRODUCT_VERSION}-installer.exe"
InstallDir "$PROGRAMFILES64\XAI"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show
RequestExecutionLevel admin

; Version Information
VIProductVersion "0.2.0.0"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey "LegalCopyright" "MIT License"
VIAddVersionKey "FileDescription" "XAI Blockchain Installer"
VIAddVersionKey "FileVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "ProductVersion" "${PRODUCT_VERSION}"

; Sections
Section "Core Files" SEC01
  SectionIn RO
  SetOutPath "$INSTDIR"

  ; Python embedded distribution
  File /r "python-${PYTHON_VERSION}-embed-amd64\*.*"

  ; XAI application
  SetOutPath "$INSTDIR\xai"
  File /r "dist\xai\*.*"

  ; Launcher scripts
  SetOutPath "$INSTDIR"
  File "xai-node.bat"
  File "xai-wallet.bat"
  File "xai-cli.bat"

  ; Icons
  File "xai.ico"
  File "xai-wallet.ico"

  ; Documentation
  SetOutPath "$INSTDIR\docs"
  File "..\..\README.md"
  File "..\..\LICENSE"
  File "..\INSTALL.md"

  ; Configuration
  SetOutPath "$APPDATA\XAI\config"
  File /nonfatal "config\*.*"
  File /oname=genesis.json "genesis.json"

  ; Create data directories
  CreateDirectory "$APPDATA\XAI\blockchain"
  CreateDirectory "$APPDATA\XAI\wallets"
  CreateDirectory "$APPDATA\XAI\state"
  CreateDirectory "$APPDATA\XAI\logs"
SectionEnd

Section "Start Menu Shortcuts" SEC02
  CreateDirectory "$SMPROGRAMS\XAI Blockchain"
  CreateShortCut "$SMPROGRAMS\XAI Blockchain\XAI Node.lnk" "$INSTDIR\xai-node.bat" "" "$INSTDIR\xai.ico"
  CreateShortCut "$SMPROGRAMS\XAI Blockchain\XAI Wallet.lnk" "$INSTDIR\xai-wallet.bat" "" "$INSTDIR\xai-wallet.ico"
  CreateShortCut "$SMPROGRAMS\XAI Blockchain\XAI Console.lnk" "$INSTDIR\xai-cli.bat" "" "$INSTDIR\xai.ico"
  CreateShortCut "$SMPROGRAMS\XAI Blockchain\Uninstall.lnk" "$INSTDIR\uninst.exe"
  CreateShortCut "$SMPROGRAMS\XAI Blockchain\Documentation.lnk" "$INSTDIR\docs\README.md"
SectionEnd

Section "Desktop Shortcuts" SEC03
  CreateShortCut "$DESKTOP\XAI Node.lnk" "$INSTDIR\xai-node.bat" "" "$INSTDIR\xai.ico"
SectionEnd

Section "Add to PATH" SEC04
  ; Add to system PATH
  EnVar::SetHKLM
  EnVar::AddValue "PATH" "$INSTDIR"
SectionEnd

Section "Auto-start on Boot" SEC05
  CreateShortCut "$SMSTARTUP\XAI Node.lnk" "$INSTDIR\xai-node.bat" "" "$INSTDIR\xai.ico"
SectionEnd

; Section descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC01} "Core XAI Blockchain files (required)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC02} "Create shortcuts in Start Menu"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC03} "Create desktop shortcut for XAI Node"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC04} "Add XAI executables to system PATH"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC05} "Start XAI Node automatically on Windows startup"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section -AdditionalIcons
  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\XAI Blockchain\Website.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\xai-node.bat"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\xai.ico"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"

  ; Install Python packages
  DetailPrint "Installing Python dependencies..."
  ExecWait '"$INSTDIR\python\python.exe" -m pip install --upgrade pip' $0
  ExecWait '"$INSTDIR\python\python.exe" -m pip install -e "$INSTDIR\xai"' $0

  ; Verify installation
  DetailPrint "Verifying installation..."
  ExecWait '"$INSTDIR\xai-node.bat" --version' $0
  ${If} $0 == 0
    DetailPrint "Installation verified successfully!"
  ${Else}
    DetailPrint "Warning: Installation verification failed"
  ${EndIf}
SectionEnd

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2
  Abort
FunctionEnd

Section Uninstall
  ; Kill running processes
  ExecWait 'taskkill /F /IM xai-node.exe /T'
  Sleep 1000

  ; Remove from PATH
  EnVar::SetHKLM
  EnVar::DeleteValue "PATH" "$INSTDIR"

  ; Remove shortcuts
  Delete "$SMPROGRAMS\XAI Blockchain\*.*"
  Delete "$DESKTOP\XAI Node.lnk"
  Delete "$SMSTARTUP\XAI Node.lnk"

  ; Remove directories
  RMDir "$SMPROGRAMS\XAI Blockchain"

  ; Remove files
  Delete "$INSTDIR\${PRODUCT_NAME}.url"
  Delete "$INSTDIR\uninst.exe"
  Delete "$INSTDIR\*.bat"
  Delete "$INSTDIR\*.ico"
  RMDir /r "$INSTDIR\xai"
  RMDir /r "$INSTDIR\python"
  RMDir /r "$INSTDIR\docs"
  RMDir /r "$INSTDIR\config"

  ; Ask about data
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Do you want to remove blockchain data and wallets?$\n$\nWARNING: Make sure you have backed up your wallet keys!" IDYES RemoveData IDNO KeepData

  RemoveData:
    RMDir /r "$APPDATA\XAI"
    Goto Done

  KeepData:
    DetailPrint "Keeping blockchain data and wallets in $APPDATA\XAI"

  Done:
    RMDir "$INSTDIR"

    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
    SetAutoClose true
SectionEnd
