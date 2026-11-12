@echo off
title SpeechToTextAuxPy - Reconocimiento de Voz SAPI
chcp 65001 > nul

echo === SpeechToTextAuxPy ===
echo.
echo Instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo Error: No se pudieron instalar las dependencias.
    echo Asegurate de tener Python 3.10+ y pip instalados.
    pause
    exit /b %errorlevel%
)
echo.
echo Iniciando reconocimiento de voz...
python src/main.py

echo.
pause
