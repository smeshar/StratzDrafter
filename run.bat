@echo off
chcp 65001 > nul
title Stratz Dota 2 Custom Drafter
echo ========================================================
echo       STRATZ DOTA 2 CUSTOM DRAFTER (70%% Counters)
echo ========================================================
echo Запуск локального сервера...
start http://localhost:5000
python app.py
pause
