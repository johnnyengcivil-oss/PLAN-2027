@echo off
title Prova funcional - Banco Proprio de Composicoes
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   O ambiente ainda nao foi instalado.
    echo   Execute primeiro:  instalar.bat
    echo.
    pause
    exit /b 1
)

echo.
echo Percorrendo o fluxo completo em 6 servicos reais das bases...
echo Nenhuma escolha e gravada como definitiva.
echo.

".venv\Scripts\python.exe" prova_funcional.py --json prova\resultado.json
echo.
echo O resultado detalhado tambem foi gravado em prova\resultado.json
echo.
pause
