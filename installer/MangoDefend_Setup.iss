; MangoDefend Inno Setup Script

#define AppName "MangoDefend"
#define AppVersion "1.0.0"
#define AppPublisher "MangoDefend"
#define AppExeName "MangoDefend.exe"
#define SourceDir "MangoDefend"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
ArchitecturesInstallIn64BitMode=x64compatible
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=MangoDefend_Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ShowLanguageDialog=no

; Wizard images
WizardImageFile=..\assets\wizard_left.bmp
WizardSmallImageFile=..\assets\wizard_small.bmp
WizardImageStretch=no

[Languages]
Name: "indonesian"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Shortcut tambahan:"

[Files]
; VC++ Runtime — di-extract ke temp, install otomatis
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

; Aplikasi MangoDefend
Source: "{#SourceDir}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Install VC++ Runtime dulu (silent, skip jika sudah ada)
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/quiet /norestart"; \
  StatusMsg: "Menginstal Visual C++ Runtime..."; \
  Flags: waituntilterminated

; Buka aplikasi setelah install selesai
Filename: "{app}\{#AppExeName}"; Description: "Buka {#AppName} sekarang"; \
  Flags: nowait postinstall skipifsilent shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure InitializeWizard();
begin
  WizardForm.Color := $1C1C12;
end;
