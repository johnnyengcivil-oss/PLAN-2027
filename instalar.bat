@echo off
setlocal enabledelayedexpansion
title Instalador - Banco Proprio de Composicoes

REM ===========================================================================
REM instalar.bat - Executa o passo 2 da implantacao (ambiente e bibliotecas).
REM
REM Basta dar DUPLO CLIQUE neste arquivo. Nao precisa abrir o Prompt de
REM Comando nem digitar nada.
REM
REM Nao exige privilegio de administrador.
REM ===========================================================================

cd /d "%~dp0"

echo.
echo ========================================================================
echo   INSTALADOR - BANCO PROPRIO DE COMPOSICOES
echo ========================================================================
echo   Pasta: %CD%
echo.

REM ------------------------------------------------- 0. Arquivos do projeto
if not exist "requirements.txt" (
    echo   [ERRO] Este arquivo nao esta na pasta do sistema.
    echo.
    echo   Esperado encontrar requirements.txt ao lado de instalar.bat.
    echo   Se voce baixou o ZIP, extraia TODO o conteudo e execute o
    echo   instalar.bat que esta dentro da pasta extraida.
    echo.
    pause
    exit /b 1
)

REM --------------------------------------------------------------- 1. Python
echo [1/4] Procurando o Python...

set "PY="
REM O lancador "py" e preferido: evita o atalho da Microsoft Store, que
REM abre a loja em vez de executar o Python.
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PY=py -3"
) else (
    python --version >nul 2>&1
    if not errorlevel 1 set "PY=python"
)

if not defined PY (
    echo.
    echo   [ERRO] Python nao encontrado nesta maquina.
    echo.
    echo   Instale a partir de:  https://www.python.org/downloads/
    echo.
    echo   IMPORTANTE: na primeira tela do instalador, MARQUE a caixa
    echo               "Add Python to PATH" antes de clicar em Install.
    echo.
    echo   Depois de instalar, feche esta janela e execute este arquivo
    echo   novamente.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('%PY% --version 2^>^&1') do set "VERSAO=%%v"
echo       Python !VERSAO! encontrado.

REM --------------------------------------------------------- 2. Ambiente
echo.
echo [2/4] Preparando o ambiente isolado (.venv)...

if exist ".venv\Scripts\python.exe" (
    echo       Ambiente ja existe, reaproveitando.
) else (
    %PY% -m venv .venv
    if errorlevel 1 (
        echo.
        echo   [ERRO] Nao foi possivel criar o ambiente virtual.
        echo   Verifique se ha espaco em disco e se a pasta nao esta
        echo   sincronizada por OneDrive/Dropbox durante a instalacao.
        echo.
        pause
        exit /b 1
    )
    echo       Ambiente criado.
)

REM ------------------------------------------------------- 3. Bibliotecas
echo.
echo [3/4] Instalando as bibliotecas ^(pode levar alguns minutos^)...
echo.

".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo   [ERRO] Falha ao instalar as bibliotecas.
    echo.
    echo   Se a empresa usa proxy ou inspecao de rede, tente:
    echo.
    echo     .venv\Scripts\python -m pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
    echo.
    pause
    exit /b 1
)

echo.
echo       Bibliotecas instaladas.

REM ------------------------------------------------------- 4. Verificacao
echo.
echo [4/4] Verificando a instalacao...
echo.

".venv\Scripts\python.exe" verificar.py
set "RESULTADO=%errorlevel%"

echo.
echo ========================================================================
if "%RESULTADO%"=="0" (
    echo   PASSO 2 CONCLUIDO. O ambiente esta pronto.
) else (
    echo   AMBIENTE PRONTO, mas ainda faltam itens - veja as linhas [FALTA]
    echo   acima. O mais comum e faltar copiar as bases.
    echo.
    echo   Copie os cinco arquivos de base para a pasta:
    echo     %CD%\BASES
    echo.
    echo   Depois execute este arquivo novamente.
)
echo ========================================================================
echo.
pause
