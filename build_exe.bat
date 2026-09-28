@echo off
chcp 65001 >nul
title Сборка Standalone EXE для StratzDrafter

echo ========================================================
echo       СБОРКА АВТОНОМНОГО EXE (БЕЗ НЕОБХОДИМОСТИ PYTHON)
echo ========================================================
echo.

echo [1/3] Проверка и установка PyInstaller...
python -m pip install pyinstaller

echo.
echo [2/3] Сборка приложения в папку dist/StratzDrafter...
python -m PyInstaller ^
    --noconfirm ^
    --onedir ^
    --console ^
    --name "StratzDrafter" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "data;data" ^
    --add-data "aliases.py;." ^
    --add-data "stratz_client.py;." ^
    app.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сборка завершилась с ошибкой.
    pause
    exit /b 1
)

echo.
echo [3/3] Копирование файла run.bat в папку dist/StratzDrafter...
copy /y "%~dp0run.bat" "%~dp0dist\StratzDrafter\" >nul

echo.
echo ========================================================
echo   Сборка завершена успешно!
echo   Готовая папка находится в: dist\StratzDrafter
echo ========================================================
echo.
pause
