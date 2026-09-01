@echo off
REM ===========================================================================
REM _localizar_python.bat - Descobre qual Python usar e devolve em PY_EXE.
REM
REM Chamado pelos outros scripts com  call "%~dp0_localizar_python.bat"
REM Nao usa setlocal de proposito: a variavel precisa chegar a quem chamou.
REM
REM Ordem de preferencia:
REM   1. python-portatil\python.exe      (Python portatil, nada instalado)
REM   2. python-portatil\<subpasta>\python.exe
REM      O Windows costuma criar uma subpasta com o nome do .zip ao
REM      extrair. Procurar um nivel abaixo evita o "Python nao
REM      encontrado" quando o arquivo foi extraido dessa maneira.
REM   3. .venv\Scripts\python.exe        (ambiente ja preparado)
REM   4. py -3                           (lancador do Windows)
REM   5. python                          (PATH)
REM ===========================================================================

set "PY_EXE="
set "PY_TIPO="

if exist "%~dp0python-portatil\python.exe" (
    set "PY_EXE=%~dp0python-portatil\python.exe"
    set "PY_TIPO=portatil"
    goto :eof
)

REM Extraido dentro de uma subpasta: aceita assim mesmo.
for /d %%D in ("%~dp0python-portatil\*") do (
    if exist "%%~fD\python.exe" (
        set "PY_EXE=%%~fD\python.exe"
        set "PY_TIPO=portatil"
        goto :eof
    )
)

REM Extraido solto na pasta do sistema, sem a pasta python-portatil.
if exist "%~dp0python.exe" (
    if exist "%~dp0python311.zip" (
        set "PY_EXE=%~dp0python.exe"
        set "PY_TIPO=portatil"
        goto :eof
    )
)

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
    set "PY_TIPO=ambiente"
    goto :eof
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_EXE=py -3"
    set "PY_TIPO=instalado"
    goto :eof
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PY_EXE=python"
    set "PY_TIPO=instalado"
)

goto :eof
