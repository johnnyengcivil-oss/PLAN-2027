@echo off
setlocal enabledelayedexpansion
title Instalador - Banco Proprio de Composicoes

REM ===========================================================================
REM instalar.bat - Prepara o ambiente Python.
REM
REM DUPLO CLIQUE. Nao precisa digitar nada, nem ser administrador.
REM
REM Funciona de tres maneiras, nesta ordem:
REM   1. Python PORTATIL na pasta python-portatil\  (nada instalado)
REM   2. Python instalado na maquina
REM   3. Se nao houver nenhum, explica como resolver
REM
REM As bibliotecas vem prontas em libs\ - a instalacao NAO precisa de
REM internet.
REM ===========================================================================

cd /d "%~dp0"

set "PAUSAR=1"
if /i "%~1"=="--sem-pausa" set "PAUSAR=0"

echo.
echo ========================================================================
echo   INSTALADOR - BANCO PROPRIO DE COMPOSICOES
echo ========================================================================
echo   Pasta: %CD%
echo.

if not exist "requirements.txt" (
    echo   [ERRO] Este arquivo nao esta na pasta do sistema.
    echo   Se voce baixou o ZIP, extraia TODO o conteudo e execute o
    echo   instalar.bat que esta dentro da pasta extraida.
    echo.
    if "%PAUSAR%"=="1" pause
    exit /b 1
)

REM --------------------------------------------------------------- 1. Python
echo [1/3] Procurando o Python...

call "%~dp0_localizar_python.bat"

if not defined PY_EXE (
    echo.
    echo   Python nao encontrado. Ha duas opcoes:
    echo.
    echo   ------------------------------------------------------------------
    echo   OPCAO A - PORTATIL, sem instalar nada  ^(recomendada^)
    echo   ------------------------------------------------------------------
    echo     1. Baixe o arquivo:
    echo        https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
    echo     2. Extraia o conteudo dele dentro de uma pasta chamada
    echo        python-portatil  AQUI NESTA PASTA, de modo que exista:
    echo          %CD%\python-portatil\python.exe
    echo     3. Execute este instalar.bat de novo.
    echo.
    echo     Nao instala nada no Windows, nao mexe no registro e nao
    echo     precisa de administrador. Para desinstalar, apague a pasta.
    echo.
    echo   ------------------------------------------------------------------
    echo   OPCAO B - Instalar o Python normalmente
    echo   ------------------------------------------------------------------
    echo     1. Baixe em https://www.python.org/downloads/
    echo     2. Na PRIMEIRA tela do instalador, MARQUE a caixa
    echo        "Add Python to PATH"  ^(vem desmarcada^)
    echo     3. Execute este instalar.bat de novo.
    echo.
    echo   Abrindo a pagina de download para voce...
    start "" "https://www.python.org/downloads/windows/"
    echo.
    if "%PAUSAR%"=="1" pause
    exit /b 1
)

for /f "tokens=2" %%v in ('%PY_EXE% --version 2^>^&1') do set "VERSAO=%%v"
echo       Python !VERSAO! ^(!PY_TIPO!^)

REM ------------------------------------------------------- 2. ambiente
echo.
echo [2/3] Preparando o ambiente...

if "!PY_TIPO!"=="portatil" (
    echo       Python portatil: as bibliotecas vao direto para ele.
) else if "!PY_TIPO!"=="ambiente" (
    echo       Ambiente .venv ja existe, reaproveitando.
) else (
    if not exist ".venv\Scripts\python.exe" (
        %PY_EXE% -m venv .venv
        if errorlevel 1 (
            echo   [ERRO] Nao foi possivel criar o ambiente virtual.
            echo   Verifique o espaco em disco e se a pasta nao esta sendo
            echo   sincronizada por OneDrive durante a instalacao.
            echo.
            if "%PAUSAR%"=="1" pause
            exit /b 1
        )
        echo       Ambiente .venv criado.
    )
    call "%~dp0_localizar_python.bat"
)

REM ------------------------------------------------------- 3. bibliotecas
echo.
echo [3/3] Instalando as bibliotecas ^(a partir de libs\, sem internet^)...
echo.

%PY_EXE% preparar_libs.py
if errorlevel 1 (
    echo.
    echo   [ERRO] Nao foi possivel preparar as bibliotecas.
    echo   Veja as linhas [FALTA] acima.
    echo.
    if "%PAUSAR%"=="1" pause
    exit /b 1
)

echo.
echo ------------------------------------------------------------------------
%PY_EXE% verificar.py
set "RESULTADO=%errorlevel%"

echo.
echo ========================================================================
if "%RESULTADO%"=="0" (
    echo   AMBIENTE PRONTO.
) else (
    echo   AMBIENTE PRONTO, mas faltam itens - veja as linhas [FALTA] acima.
    echo   O mais comum e faltar copiar as bases para a pasta BASES.
)
echo ========================================================================
echo.
if "%PAUSAR%"=="1" pause
exit /b %RESULTADO%
