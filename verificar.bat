@echo off
title Verificacao - Banco Proprio de Composicoes
cd /d "%~dp0"

call "%~dp0_localizar_python.bat"

if not defined PY_EXE (
    echo.
    echo   O ambiente ainda nao foi preparado.
    echo   Execute primeiro:  instalar.bat
    echo.
    pause
    exit /b 1
)

%PY_EXE% verificar.py
echo.
pause
