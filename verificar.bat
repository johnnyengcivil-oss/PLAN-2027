@echo off
title Verificacao - Banco Proprio de Composicoes
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   O ambiente ainda nao foi instalado.
    echo   Execute primeiro:  instalar.bat
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" verificar.py
echo.
pause
