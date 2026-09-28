@echo off
chcp 65001 >nul
cls
echo ========================================================
echo        STRATZ DRAFTER - TEST RUNNER
echo ========================================================
echo.

if "%1"=="unit" goto run_unit
if "%1"=="api" goto run_api
if "%1"=="e2e" goto run_e2e
if "%1"=="all" goto run_all
if "%1"=="headed" goto run_headed

echo Выберите тип тестирования:
echo   [1] Запустить ВСЕ тесты (Unit + API + E2E браузер)
echo   [2] Быстрые модульные и API тесты (pytest -m "unit or api")
echo   [3] E2E тесты веб-интерфейса в браузере (Playwright)
echo   [4] E2E тесты с отображением браузера (--headed)
echo.
set /p choice="Ваш выбор (1-4, по умолчанию 1): "

if "%choice%"=="2" goto run_unit
if "%choice%"=="3" goto run_e2e
if "%choice%"=="4" goto run_headed
goto run_all

:run_unit
echo.
echo [TESTS] Запуск модульных и API тестов...
echo --------------------------------------------------------
python -m pytest -m "unit or api" --tb=short
goto finish

:run_api
echo.
echo [TESTS] Запуск API тестов...
echo --------------------------------------------------------
python -m pytest tests/test_api.py --tb=short
goto finish

:run_e2e
echo.
echo [TESTS] Запуск Playwright E2E тестов в браузере...
echo --------------------------------------------------------
python -m pytest tests/test_e2e_browser.py --tb=short
goto finish

:run_headed
echo.
echo [TESTS] Запуск E2E тестов с отображением окна браузера...
echo --------------------------------------------------------
python -m pytest tests/test_e2e_browser.py --headed --tb=short
goto finish

:run_all
echo.
echo [TESTS] Запуск ВСЕХ тестов проекта...
echo --------------------------------------------------------
python -m pytest --tb=short
goto finish

:finish
echo.
echo ========================================================
echo   Тестирование завершено!
echo ========================================================
echo.
pause
