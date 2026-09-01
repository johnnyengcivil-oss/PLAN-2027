@echo off
setlocal enabledelayedexpansion
title Banco Proprio de Composicoes - Instalacao completa

REM ===========================================================================
REM COMECAR_AQUI.bat - Faz a implantacao inteira, do zero ao Excel pronto.
REM
REM DUPLO CLIQUE NESTE ARQUIVO. Nao precisa digitar nada.
REM Nao exige privilegio de administrador.
REM ===========================================================================

cd /d "%~dp0"

echo.
echo ========================================================================
echo   BANCO PROPRIO DE COMPOSICOES
echo   Instalacao completa
echo ========================================================================
echo.
echo   Este script faz, em sequencia:
echo     1. prepara o ambiente Python
echo     2. importa as cinco bases ^(sem alterar os arquivos originais^)
echo     3. monta a planilha do Excel com as macros
echo.
echo   Pressione uma tecla para comecar, ou feche a janela para desistir.
pause >nul

REM ------------------------------------------------ pasta gravavel?
REM A raiz do disco (C:\) e as Arquivos de Programas exigem privilegio de
REM administrador para gravar. O sistema precisa criar o banco, o
REM config.json e a pasta _temp aqui, entao uma pasta protegida trava tudo
REM - e pior, uma extracao para la pode ter deixado arquivos para tras sem
REM avisar. Melhor descobrir agora do que no meio do caminho.
echo teste> "%~dp0_permissao.tmp" 2>nul
if not exist "%~dp0_permissao.tmp" (
    echo.
    echo ========================================================================
    echo   ESTA PASTA E PROTEGIDA PELO WINDOWS
    echo ========================================================================
    echo.
    echo   Pasta atual:
    echo     %CD%
    echo.
    echo   Nao consigo gravar aqui sem privilegio de administrador. O sistema
    echo   precisa criar o banco de dados e arquivos temporarios na propria
    echo   pasta, entao ele nao funciona neste lugar.
    echo.
    echo   SOLUCAO: mova a pasta inteira para um lugar seu, por exemplo:
    echo.
    echo     %USERPROFILE%\Documents\BANCO_COMPOSICOES
    echo     %USERPROFILE%\Desktop\BANCO_COMPOSICOES
    echo.
    echo   Depois execute o COMECAR_AQUI.bat de la.
    echo.
    echo   Abrindo a sua pasta Documentos...
    start "" "%USERPROFILE%\Documents"
    echo.
    pause
    exit /b 1
)
del "%~dp0_permissao.tmp" >nul 2>&1

REM ------------------------------------------------------------------ etapa 1
echo.
echo ########################################################################
echo #  ETAPA 1 de 3 - AMBIENTE
echo ########################################################################
call "%~dp0instalar.bat" --sem-pausa
if errorlevel 1 (
    echo.
    echo   A etapa 1 nao foi concluida. Resolva o que foi indicado acima
    echo   e execute este arquivo novamente.
    echo.
    pause
    exit /b 1
)

REM ------------------------------------------------------------------ etapa 2
echo.
echo ########################################################################
echo #  ETAPA 2 de 3 - BASES
echo ########################################################################
echo.
echo Importando as cinco bases...
echo ^(os arquivos originais sao abertos SOMENTE PARA LEITURA^)
echo.

call "%~dp0_localizar_python.bat"
%PY_EXE% python\main.py --json "{\"acao\":\"atualizar_bases\"}" >nul
%PY_EXE% verificar.py
if errorlevel 1 (
    echo.
    echo   Faltam itens - veja as linhas [FALTA] acima.
    echo   O mais comum e faltar copiar as bases para a pasta BASES.
    echo.
    pause
    exit /b 1
)

REM ------------------------------------------------------------------ etapa 3
echo.
echo ########################################################################
echo #  ETAPA 3 de 3 - PLANILHA
echo ########################################################################
call "%~dp0MONTAR_PLANILHA.bat"

exit /b 0
