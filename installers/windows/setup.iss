; Inno Setup Script for XAI Blockchain
; Builds a Windows installer (.exe) with embedded Python distribution
; Requires Inno Setup 6.2+ from https://jrsoftware.org/isinfo.php

#define MyAppName "XAI Blockchain"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "XAI Blockchain Team"
#define MyAppURL "https://xai-blockchain.io"
#define MyAppExeName "xai-node.exe"
#define PythonVersion "3.12.1"

[Setup]
AppId={{B7F3C8A5-4E2D-4B9A-8C1F-3D5E6A7F9B2C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\XAI
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\..\LICENSE
InfoBeforeFile=README.txt
OutputDir=.\output
OutputBaseFilename=xai-blockchain-{#MyAppVersion}-setup
SetupIconFile=xai.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\xai.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "addtopath"; Description: "Add XAI executables to PATH"; GroupDescription: "System Integration:"; Flags: checked
Name: "startmenu"; Description: "Create Start Menu shortcuts"; GroupDescription: "System Integration:"; Flags: checked
Name: "autostart"; Description: "Start XAI Node on Windows startup"; GroupDescription: "System Integration:"; Flags: unchecked

[Files]
; Python embedded distribution (download separately)
Source: "python-{#PythonVersion}-embed-amd64\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs
; XAI package and dependencies
Source: "dist\xai\*"; DestDir: "{app}\xai"; Flags: ignoreversion recursesubdirs createallsubdirs
; Launcher scripts
Source: "xai-node.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "xai-wallet.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "xai-cli.bat"; DestDir: "{app}"; Flags: ignoreversion
; Configuration and data
Source: "config\*"; DestDir: "{commonappdata}\XAI\config"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist
Source: "genesis.json"; DestDir: "{commonappdata}\XAI\config"; Flags: ignoreversion onlyifdoesntexist
; Documentation
Source: "..\..\README.md"; DestDir: "{app}\docs"; Flags: ignoreversion isreadme
Source: "..\..\LICENSE"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\INSTALL.md"; DestDir: "{app}\docs"; Flags: ignoreversion
; Icons
Source: "xai.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "xai-wallet.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\XAI Node"; Filename: "{app}\xai-node.bat"; IconFilename: "{app}\xai.ico"; Comment: "Start XAI Blockchain Node"
Name: "{group}\XAI Wallet"; Filename: "{app}\xai-wallet.bat"; IconFilename: "{app}\xai-wallet.ico"; Comment: "XAI Wallet Manager"
Name: "{group}\XAI Console"; Filename: "{app}\xai-cli.bat"; IconFilename: "{app}\xai.ico"; Comment: "XAI Command Line Interface"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\XAI Node"; Filename: "{app}\xai-node.bat"; IconFilename: "{app}\xai.ico"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\XAI Node"; Filename: "{app}\xai-node.bat"; IconFilename: "{app}\xai.ico"; Tasks: quicklaunchicon
Name: "{autostartup}\XAI Node"; Filename: "{app}\xai-node.bat"; IconFilename: "{app}\xai.ico"; Tasks: autostart

[Registry]
; Add to PATH
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath('{app}')

[Run]
Filename: "{app}\xai-node.bat"; Parameters: "--version"; Flags: runhidden waituntilterminated; StatusMsg: "Verifying installation..."
Filename: "{app}\docs\README.md"; Description: "{cm:LaunchProgram,README}"; Flags: postinstall shellexec skipifsilent unchecked
Filename: "{app}\xai-node.bat"; Description: "Start XAI Node"; Flags: postinstall nowait skipifsilent unchecked

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM xai-node.exe /T"; Flags: runhidden; RunOnceId: "KillXAINode"

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  DataDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    DataDir := ExpandConstant('{commonappdata}\XAI');

    // Create data directories
    if not DirExists(DataDir + '\blockchain') then
      CreateDir(DataDir + '\blockchain');
    if not DirExists(DataDir + '\wallets') then
      CreateDir(DataDir + '\wallets');
    if not DirExists(DataDir + '\state') then
      CreateDir(DataDir + '\state');
    if not DirExists(DataDir + '\logs') then
      CreateDir(DataDir + '\logs');

    // Set up Python environment
    Exec(ExpandConstant('{app}\python\python.exe'), '-m pip install --upgrade pip', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec(ExpandConstant('{app}\python\python.exe'), '-m pip install -e ' + ExpandConstant('{app}\xai'), '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
  Response: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    DataDir := ExpandConstant('{commonappdata}\XAI');

    Response := MsgBox('Do you want to remove blockchain data and wallets?' + #13#10 +
                      'This will delete all local blockchain data and wallet files.' + #13#10 + #13#10 +
                      'WARNING: Make sure you have backed up your wallet keys!',
                      mbConfirmation, MB_YESNO);

    if Response = IDYES then
    begin
      DelTree(DataDir, True, True, True);
    end;
  end;
end;
