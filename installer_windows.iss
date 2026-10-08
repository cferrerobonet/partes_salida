#define MyAppName "Partes de salida"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppPublisher "Carlos Ferrero Bonet"
#define MyAppExeName "PartesDeSalida.exe"

[Setup]
AppId={{6E2B3C41-9F0A-4C3E-8B7D-5A1F2E9C4D70}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Partes de salida
DefaultGroupName=Partes de salida
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputDir=Output
OutputBaseFilename=PartesDeSalida-{#MyAppVersion}-Windows-Setup
ArchitecturesInstallIn64BitMode=x64compatible
; Sin exigir administrador: en el centro casi nadie lo es (BLD-006 de Guardias).
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll,*.pyd
RestartApplications=no
SetupIconFile=imagenes\icono.ico

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear icono en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "dist\PartesDeSalida\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Partes de salida"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Partes de salida"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Partes de salida"; Flags: nowait postinstall skipifsilent

[Code]
{ La app sigue abierta en la bandeja aunque se cierre la ventana: se pide que se
  cierre antes de copiar (CloseApplications). Los datos del usuario viven en
  %APPDATA%\PartesSalida, fuera del programa, y desinstalar no los toca. }

function DesinstaladorAnterior(): String;
var
  Clave: String;
  Valor: String;
begin
  Result := '';
  Clave := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' +
           ExpandConstant('{#SetupSetting("AppId")}') + '_is1';
  if RegQueryStringValue(HKCU, Clave, 'UninstallString', Valor) then
    Result := Valor
  else if RegQueryStringValue(HKLM, Clave, 'UninstallString', Valor) then
    Result := Valor;
  Result := RemoveQuotes(Result);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Desinstalador: String;
  Codigo: Integer;
  Espera: Integer;
begin
  Result := '';
  Desinstalador := DesinstaladorAnterior();
  if (Desinstalador = '') or (not FileExists(Desinstalador)) then
    exit;
  if not Exec(Desinstalador, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '',
              SW_HIDE, ewWaitUntilTerminated, Codigo) then
    exit;
  Espera := 0;
  while FileExists(Desinstalador) and (Espera < 60) do
  begin
    Sleep(500);
    Espera := Espera + 1;
  end;
end;
