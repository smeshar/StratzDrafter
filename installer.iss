; ========================================================
;  STRATZ CUSTOM DRAFTER - INNO SETUP SCRIPT
;  Скрипт для сборки установщика StratzDrafter_Setup.exe
; ========================================================

#define MyAppName "Stratz Custom Drafter"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "noootle"
#define MyAppURL "https://github.com/smeshar/StratzDrafter"
#define MyAppExeName "run.bat"

[Setup]
AppId={{D07A2026-578A-4D8A-9F7C-DRAFTER2026}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\StratzDrafter
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=StratzDrafter_Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Основные исполняемые файлы и модули
Source: "app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "stratz_client.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "aliases.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "run.bat"; DestDir: "{app}"; Flags: ignoreversion

; Директории шаблонов, статики и кэша
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: shellexec postinstall nowait skipifsilent

[Code]
var
  TokenPage: TInputQueryWizardPage;

// 1. Создаем страницу мастера для ввода токена Stratz API
procedure InitializeWizard;
begin
  TokenPage := CreateInputQueryPage(
    wpSelectDir,
    'Настройка Stratz API',
    'Введите ваш персональный токен Stratz (необязательно)',
    'Токен API используется для загрузки актуальной статистики и обновлений матчапов.'#13#10 +
    'Получить бесплатный токен можно на: https://stratz.com/api'#13#10#13#10 +
    'Если у вас пока нет токена, просто оставьте поле пустым —'#13#10 +
    'приложение будет работать на встроенной локальной базе данных!'
  );
  TokenPage.Add('STRATZ API Token:', False);
end;

// 2. После копирования файлов сохраняем токен в .env и устанавливаем библиотеки
procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvFilePath: String;
  TokenValue: String;
  EnvContent: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Сохранение .env
    TokenValue := Trim(TokenPage.Values[0]);
    EnvFilePath := ExpandConstant('{app}\.env');
    EnvContent := 'STRATZ_API=' + TokenValue;
    SaveStringToFile(EnvFilePath, EnvContent, False);

    // Установка зависимостей через pip (в фоновом режиме)
    Exec(
      'python',
      '-m pip install -r "' + ExpandConstant('{app}\requirements.txt') + '"',
      '',
      SW_HIDE,
      ewWaitUntilTerminated,
      ResultCode
    );
  end;
end;
