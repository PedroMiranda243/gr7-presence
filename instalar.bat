@echo off
rem Instalador do GR7 Presence: o trabalho fica no tools\instalar.ps1.
cd /d "%~dp0"
title GR7 Presence - instalacao
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\instalar.ps1" %*
if /i "%~1"=="-Teste" exit /b %errorlevel%
echo.
pause
