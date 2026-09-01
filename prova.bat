@echo off
title Prova funcional - Banco Proprio de Composicoes
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

echo.
echo Percorrendo o fluxo completo em 6 servicos reais das bases...
echo Nenhuma escolha e gravada como definitiva.
echo.
%PY_EXE% prova_funcional.py --json prova\resultado.json
echo.
pause
