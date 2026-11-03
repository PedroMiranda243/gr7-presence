@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo Fechando o GR7 Presence...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' or Name='python.exe'\" | Where-Object { $_.CommandLine -like '*gr7_presence*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo Removendo atalhos...
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\GR7 Presence.lnk" 2>nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\GR7 Presence.lnk" 2>nul

echo.
echo Pronto. Suas estatisticas e configuracoes continuam na pasta "dados" do projeto.
echo Apague a pasta do projeto se quiser remover tudo.
pause
