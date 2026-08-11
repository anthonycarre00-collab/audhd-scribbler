; Inno Setup definition for the self-contained Windows Scribbler build.
#define AppName "The Audhd Scribbler"
#define AppVersion "2.0.0"
#define Publisher "The Audhd Scribbler"
#define ExeName "ScribblerWindows.exe"

[Setup]
AppId={{D8A6D0D5-0B2A-4F2D-9D3B-3B5E5F8D5C11}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#Publisher}
DefaultDirName={autopf}\Audhd Scribbler
DefaultGroupName={#AppName}
OutputDir=dist
OutputBaseFilename=Audhd-Scribbler-Windows-Installer
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#ExeName}

[Files]
Source: "..\dist\{#ExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; WorkingDir: "{app}"
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#ExeName}"; Description: "Open The Audhd Scribbler"; Flags: nowait postinstall skipifsilent
