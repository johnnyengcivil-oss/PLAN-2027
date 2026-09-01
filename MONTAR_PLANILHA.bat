@echo off
setlocal enabledelayedexpansion
title Montar planilha - Banco Proprio de Composicoes

REM ===========================================================================
REM MONTAR_PLANILHA.bat
REM
REM Gera Sistema_Composicoes.xlsm com os 10 modulos VBA ja dentro.
REM Basta dar DUPLO CLIQUE. Nao exige privilegio de administrador.
REM
REM O QUE ESTE SCRIPT FAZ COM O REGISTRO DO WINDOWS
REM -----------------------------------------------
REM Para inserir os modulos, o Excel exige a opcao
REM   "Confiar no acesso ao modelo de objeto do projeto do VBA".
REM Ela e a chave AccessVBOM em HKEY_CURRENT_USER (so do seu usuario,
REM nao afeta a maquina nem outros usuarios).
REM
REM O script pede sua autorizacao, LIGA a opcao, monta a planilha e
REM DEVOLVE a opcao ao valor anterior - inclusive se algo der errado.
REM
REM Se preferir nao mexer nisso, responda N: o script gera o .xlsx e
REM mostra como importar os modulos manualmente (uma unica arrastada).
REM ===========================================================================

cd /d "%~dp0"

echo.
echo ========================================================================
echo   MONTAR A PLANILHA DO SISTEMA
echo ========================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo   [ERRO] O ambiente ainda nao foi instalado.
    echo   Execute primeiro:  instalar.bat
    echo.
    pause
    exit /b 1
)

REM ------------------------------------------------- 1. gerar a pasta base
echo [1/3] Gerando a pasta de trabalho com as 9 abas...
".venv\Scripts\python.exe" build_xlsm.py >nul
if errorlevel 1 (
    echo   [ERRO] Falha ao gerar Sistema_Composicoes.xlsx
    pause
    exit /b 1
)
echo       Sistema_Composicoes.xlsx gerado.
echo.

REM ------------------------------------------- 2. localizar a versao do Office
echo [2/3] Procurando o Excel instalado...

set "CHAVE="
for %%V in (16.0 15.0 14.0 12.0) do (
    if not defined CHAVE (
        reg query "HKCU\Software\Microsoft\Office\%%V\Excel" >nul 2>&1
        if not errorlevel 1 set "CHAVE=HKCU\Software\Microsoft\Office\%%V\Excel\Security"
    )
)

if not defined CHAVE (
    echo   [AVISO] Nao localizei a instalacao do Excel no registro.
    echo   Vou tentar mesmo assim.
    set "CHAVE=HKCU\Software\Microsoft\Office\16.0\Excel\Security"
)
echo       Usando: !CHAVE!
echo.

REM guarda o valor atual para restaurar depois
set "VALOR_ANTERIOR="
set "TINHA_VALOR=0"
for /f "tokens=3" %%a in ('reg query "!CHAVE!" /v AccessVBOM 2^>nul ^| find "AccessVBOM"') do (
    set "VALOR_ANTERIOR=%%a"
    set "TINHA_VALOR=1"
)

if "!TINHA_VALOR!"=="1" (
    echo       Estado atual da opcao AccessVBOM: !VALOR_ANTERIOR!
) else (
    echo       A opcao AccessVBOM ainda nao existe ^(padrao: desligada^).
)
echo.

REM ------------------------------------------------- 3. autorizacao do usuario
echo ------------------------------------------------------------------------
echo   Para inserir os modulos, preciso LIGAR temporariamente a opcao
echo   "Confiar no acesso ao modelo de objeto do projeto do VBA".
echo.
echo   - Vale apenas para o SEU usuario do Windows ^(HKEY_CURRENT_USER^)
echo   - Nao exige administrador
echo   - Sera DEVOLVIDA ao estado anterior ao final, mesmo se der erro
echo ------------------------------------------------------------------------
echo.
set /p "RESP=Autoriza? (S/N): "

if /i not "!RESP!"=="S" goto MANUAL

echo.
echo [3/3] Montando a planilha...

reg add "!CHAVE!" /v AccessVBOM /t REG_DWORD /d 1 /f >nul 2>&1
if errorlevel 1 (
    echo   [ERRO] Nao foi possivel alterar a opcao.
    goto MANUAL
)

REM feche o Excel antes, senao a instancia aberta ignora a mudanca
tasklist /fi "imagename eq excel.exe" 2>nul | find /i "excel.exe" >nul
if not errorlevel 1 (
    echo.
    echo   ATENCAO: o Excel esta aberto. Feche-o e pressione uma tecla.
    pause >nul
)

cscript //nologo instalar_vba.vbs
set "RESULTADO=!errorlevel!"

REM ---------------------------------------------- restaurar o estado anterior
if "!TINHA_VALOR!"=="1" (
    reg add "!CHAVE!" /v AccessVBOM /t REG_DWORD /d !VALOR_ANTERIOR! /f >nul 2>&1
    echo.
    echo       Opcao AccessVBOM devolvida ao valor anterior ^(!VALOR_ANTERIOR!^).
) else (
    reg delete "!CHAVE!" /v AccessVBOM /f >nul 2>&1
    echo.
    echo       Opcao AccessVBOM devolvida ao estado original ^(desligada^).
)

if not "!RESULTADO!"=="0" goto MANUAL
if not exist "Sistema_Composicoes.xlsm" goto MANUAL

echo.
echo ========================================================================
echo   PLANILHA PRONTA: Sistema_Composicoes.xlsm
echo ========================================================================
echo.
echo   Abra o arquivo, habilite as macros e, na aba INICIO,
echo   clique em TESTAR MOTOR.
echo.
echo   Se o Windows bloquear as macros por o arquivo ter vindo da
echo   internet: botao direito no arquivo, Propriedades, marcar
echo   "Desbloquear" e clicar OK.
echo.
pause
exit /b 0

:MANUAL
echo.
echo ========================================================================
echo   CAMINHO MANUAL - uma unica arrastada
echo ========================================================================
echo.
echo   1. Abra Sistema_Composicoes.xlsx ^(esta nesta pasta^)
echo   2. Salve como .xlsm:
echo        Arquivo, Salvar como, tipo "Pasta de Trabalho Habilitada
echo        para Macro ^(*.xlsm^)"
echo   3. Pressione ALT + F11 para abrir o editor de macros
echo   4. Abra a pasta vba desta pasta no Explorador de Arquivos,
echo      selecione os 10 arquivos .bas ^(CTRL + A^) e ARRASTE todos
echo      de uma vez para dentro da janela do editor, do lado esquerdo
echo   5. Ainda no editor, pressione CTRL + G, digite
echo        modUI.ReconstruirBotoes
echo      e pressione ENTER ^(isso cria os botoes das abas^)
echo   6. Volte ao Excel e salve com CTRL + B
echo.
echo   Abrindo a pasta vba para voce...
start "" "%~dp0vba"
echo.
pause
exit /b 1
