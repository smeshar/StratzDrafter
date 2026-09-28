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
if not errorlevel 1 goto check_libs

set PY_CMD=py
py --version >nul 2>&1
if not errorlevel 1 goto check_libs

goto no_python

:check_libs
%PY_CMD% -c "import flask, requests, dotenv" >nul 2>&1
if not errorlevel 1 goto start_app

echo [ИНФО] Библиотеки еще не установлены. Устанавливаем зависимости...
echo --------------------------------------------------------
%PY_CMD% -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto pip_error
echo.

:start_app
echo Запуск локального сервера...
start http://localhost:5000
%PY_CMD% app.py
if errorlevel 1 goto app_error
exit /b 0

:no_python
echo [ОШИБКА] Python не найден на вашем компьютере!
echo.
echo Для работы приложения необходим Python 3.10 или новее.
echo Скачайте Python с официального сайта:
echo https://www.python.org/downloads/
echo.
echo ВАЖНО: При установке обязательно отметьте галочку "Add Python to PATH"!
echo.
pause
exit /b 1

:pip_error
echo.
echo [ОШИБКА] Не удалось автоматически установить библиотеки через pip.
echo Пожалуйста, проверьте интернет-соединение или запустите setup.bat.
echo.
pause
exit /b 1

:app_error
echo.
echo [ОШИБКА] Сервер завершил работу с ошибкой.
echo.
pause
exit /b 1
