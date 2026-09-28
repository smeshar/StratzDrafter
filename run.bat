@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Stratz Dota 2 Custom Drafter

echo ========================================================
echo        STRATZ DOTA 2 CUSTOM DRAFTER
echo ========================================================
echo.

:: 1. Проверка наличия Python
set PY_CMD=python
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if not errorlevel 1 (
        set PY_CMD=py
    ) else (
        echo [ОШИБКА] Python не найден на вашем компьютере!
        echo.
        echo Пожалуйста, запустите setup.bat для автоматической установки,
        echo либо скачайте Python с официального сайта:
        echo https://www.python.org/downloads/
        echo (обязательно отметьте галочку "Add Python to PATH")
        echo.
        pause
        exit /b 1
    )
)

:: 2. Проверка библиотек (Flask)
%PY_CMD% -c "import flask, requests, dotenv" >nul 2>&1
if errorlevel 1 (
    echo [ИНФО] Библиотеки еще не установлены. Запускаем установку...
    echo --------------------------------------------------------
    %PY_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ОШИБКА] Не удалось установить библиотеки через pip.
        echo Попробуйте запустить setup.bat от имени администратора.
        pause
        exit /b 1
    )
    echo.
)

:: 3. Запуск сервера и открытие браузера
echo Запуск локального сервера...
start http://localhost:5000
%PY_CMD% app.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сервер завершил работу с ошибкой.
    pause
)
