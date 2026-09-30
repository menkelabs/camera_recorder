; Inno Setup script for SwingLab.
; Compiled by scripts/build_installer.py after PyInstaller (Windows).
;
;   iscc /DMyAppVersion=1.1.0 packaging\swinglab.iss

#ifndef MyAppVersion
  #define MyAppVersion "1.1.0"
#endif

#ifndef SourceDir
  #define SourceDir "..\dist\SwingLab"
#endif

#ifndef OutputDir
  #define OutputDir "..\dist\installer"
#endif

#define MyAppName "SwingLab"
#define MyAppPublisher "Menke Labs"
#define MyAppURL "https://github.com/menkelabs/camera_recorder"
#define MyAppExeName "SwingLab.exe"

[Setup]
AppId={{8F3C2A71-6B0E-4D9A-9C1E-A1B2C3D4E5F6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#OutputDir}
OutputBaseFilename=SwingLab-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{#MyAppName} setup"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--setup"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--setup"; Description: "Set up cameras and the first player now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}\*.log"
