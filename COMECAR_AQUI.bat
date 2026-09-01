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

".venv\Scripts\python.exe" python\main.py --json "{\"acao\":\"atualizar_bases\"}" >nul
".venv\Scripts\python.exe" verificar.py
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
