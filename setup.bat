@echo off
chcp 65001 >nul
title Установка Stratz Custom Drafter

echo ========================================================
echo        STRATZ DOTA 2 DRAFTER - УСТАНОВЩИК
echo ========================================================
echo.

:: 1. Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден на вашем компьютере!
    echo.
    echo Чтобы приложение работало, нужен Python (3.10 или новее).
    echo Сейчас откроется страница загрузки Python.
    echo.
    echo ВАЖНО: При установке обязательно поставьте галочку:
    echo "[X] Add Python to PATH" (внизу первого окна установщика)
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Найден Python версии %PY_VER%
echo.

:: 2. Настройка STRATZ API токена
echo --------------------------------------------------------
echo                НАСТРОЙКА STRATZ API
echo --------------------------------------------------------
echo Приложению требуется токен Stratz API для загрузки
echo свежей статистики матчей и контрпиков.
echo (Получить бесплатный токен можно на: https://stratz.com/api)
echo.
echo Если у вас пока нет токена, просто нажмите Enter -
echo приложение будет работать на локальной оффлайн-базе!
echo --------------------------------------------------------
set /p TOKEN="Введите ваш STRATZ API токен (или Enter): "

if not "%TOKEN%"=="" (
    echo STRATZ_API=%TOKEN%> "%~dp0.env"
    echo [OK] Токен успешно сохранен в .env!
) else (
    if not exist "%~dp0.env" (
        echo STRATZ_API=> "%~dp0.env"
        echo [OK] Создан файл .env для работы в оффлайн-режиме.
    ) else (
        echo [OK] Оставлен существующий файл .env.
    )
)
echo.

:: 3. Установка библиотек
echo [1/2] Установка необходимых библиотек...
echo --------------------------------------------------------
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo [ПРЕДУПРЕЖДЕНИЕ] Некоторые библиотеки не смогли установиться.
    echo Проверьте подключение к интернету.
) else (
    echo [OK] Все библиотеки успешно установлены!
)
echo.

:: 4. Создание ярлыка на Рабочем столе
echo [2/2] Создание ярлыка на Рабочем столе...
set SCRIPT_DIR=%~dp0
set SHORTCUT_PATH=%USERPROFILE%\Desktop\StratzDrafter.lnk
set TARGET_PATH=%SCRIPT_DIR%run.bat

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%TARGET_PATH%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.IconLocation = 'shell32.dll,13'; $s.Description = 'Stratz Dota 2 Custom Drafter'; $s.Save()" >nul 2>&1

if exist "%SHORTCUT_PATH%" (
    echo [OK] Ярлык "StratzDrafter" успешно создан на вашем Рабочем столе!
) else (
    echo [ИНФО] Не удалось автоматически создать ярлык. Запуск доступен через run.bat.
)
echo.

:: 5. Завершение и запуск
echo ========================================================
echo        УСТАНОВКА УСПЕШНО ЗАВЕРШЕНА!
echo ========================================================
echo.
echo Вы можете запускать драфтер в любое время через
echo ярлык на Рабочем столе или двойным кликом по run.bat.
echo.
set /p LAUNCH="Запустить StratzDrafter прямо сейчас? (Y/n): "
if /i not "%LAUNCH%"=="n" (
    start "" "%~dp0run.bat"
)

exit /b 0
