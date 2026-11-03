# Instalador do GR7 Presence (chamado pelo instalar.bat).
#   -Teste  instala só o ambiente Python: não cria atalhos nem abre o programa
param([switch]$Teste)

$ErrorActionPreference = 'Stop'
trap {
    Write-Host ""
    Write-Host "  ERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Venv = Join-Path $Root '.venv\Scripts\python.exe'
$VenvW = Join-Path $Root '.venv\Scripts\pythonw.exe'
$PythonUrl = 'https://www.python.org/downloads/release/python-3119/'

function Step($text) { Write-Host ""; Write-Host "  $text" -ForegroundColor Cyan }
function Ok($text) { Write-Host "    $text" -ForegroundColor Green }
function Warn($text) { Write-Host "    $text" -ForegroundColor Yellow }
function Ask($question) {
    $answer = Read-Host "    $question (S/N)"
    return $answer -match '^\s*[sSyY]'
}

# Python 3.10 ou mais novo, de preferência o 3.11 (o testado). O Python da Microsoft Store fica de
# fora: ele redireciona o AppData para uma pasta privada, e os atalhos e dados se perderiam.
function Find-Python {
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($v in '3.11', '3.12', '3.13', '3.10', '3') { $candidates += , @('py', "-$v") }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) { $candidates += , @('python') }
    # Instalado agora pelo winget: o PATH desta janela ainda não foi atualizado.
    foreach ($pattern in "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe", "$env:ProgramFiles\Python3*\python.exe") {
        Get-Item $pattern -ErrorAction SilentlyContinue | Sort-Object FullName -Descending |
            ForEach-Object { $candidates += , @($_.FullName) }
    }
    foreach ($c in $candidates) {
        $exe = $c[0]
        $pyArgs = @($c | Select-Object -Skip 1) + @('-c', 'import sys; print(sys.version_info >= (3, 10), sys.executable)')
        try { $out = & $exe @pyArgs 2>$null } catch { continue }
        if ($LASTEXITCODE -eq 0 -and "$out" -match '^True (.+)$') {
            $path = $Matches[1].Trim()
            if ($path -notmatch '\\WindowsApps\\') { return $path }
        }
    }
    return $null
}

Write-Host ""
Write-Host "  === GR7 Presence: Discord Rich Presence para o Guitar Rig 7 ===" -ForegroundColor White

# ---- 1. Python -------------------------------------------------------------------------------
Step "[1/5] Procurando o Python..."
if (Test-Path $Venv) {
    Ok "Ambiente Python já existe (.venv)."
} else {
    $python = Find-Python
    if (-not $python) {
        Warn "Não encontrei o Python 3.10 ou mais novo (o da Microsoft Store não serve)."
        if (-not $Teste -and (Get-Command winget -ErrorAction SilentlyContinue) -and (Ask "Instalar o Python 3.11 agora? (uns 30 MB)")) {
            winget install -e --id Python.Python.3.11 --scope user --accept-package-agreements --accept-source-agreements
            $python = Find-Python
        }
    }
    if (-not $python) {
        Write-Host ""
        Warn "Instale o Python 3.11 pelo site e rode o instalar.bat de novo:"
        Warn "  1. Baixe 'Windows installer (64-bit)' em $PythonUrl"
        Warn "  2. Na primeira tela do instalador, MARQUE 'Add python.exe to PATH'"
        Warn "  3. Clique em 'Install Now'"
        if (-not $Teste) { Start-Process $PythonUrl }
        exit 1
    }
    Ok "Usando $python"
    Step "[2/5] Criando o ambiente Python (.venv)..."
    & $python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Não consegui criar o ambiente Python." }
    Ok "Pronto."
}

# ---- 2. Dependências -------------------------------------------------------------------------
Step "[3/5] Instalando as dependências (pode levar 1 ou 2 minutos)..."
& $Venv -m pip install --disable-pip-version-check -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências. Confira a internet e tente de novo." }
Ok "psutil, pystray e Pillow instalados."
& $Venv -m pip install --disable-pip-version-check -q -r requirements-ocr.txt
if ($LASTEXITCODE -eq 0) {
    Ok "OCR do Windows instalado (preset ao vivo)."
} else {
    Warn "Não consegui instalar o OCR do Windows. O programa funciona, mas sem ler o preset ao vivo"
    Warn "(mostra o preset salvo quando o Guitar Rig fechou). Python 3.11 resolve isso."
}

# ---- 3. Conferências -------------------------------------------------------------------------
Step "[4/5] Conferindo o computador..."
if (Test-Path 'C:\Program Files\Native Instruments\Guitar Rig 7\Guitar Rig 7.exe') {
    Ok "Guitar Rig 7 encontrado."
    # O ícone oficial é da Native Instruments e não vem no zip: sai do Guitar Rig instalado aqui.
    & $Venv tools\make_assets.py --locais | Out-Null
    if ($LASTEXITCODE -eq 0) { Ok "Ícone do Guitar Rig copiado para a bandeja." }
    else { Warn "Não consegui copiar o ícone do Guitar Rig; a bandeja usa um ícone simples." }
} else {
    Warn "Não achei o Guitar Rig 7 no local padrão. Tudo bem se ele estiver em outra pasta:"
    Warn "o GR7 Presence reconhece o programa aberto, esteja onde estiver."
}
if (Get-Process -Name Discord, DiscordPTB, DiscordCanary -ErrorAction SilentlyContinue) {
    Ok "Discord aberto."
} else {
    Warn "O Discord desktop não está aberto agora (o Discord no navegador não mostra Rich Presence)."
}

if ($Teste) {
    Write-Host ""
    Ok "Modo teste: sem atalhos e sem abrir o programa."
    exit 0
}

# ---- 4. Atalhos ------------------------------------------------------------------------------
Step "[5/5] Criando o atalho no Menu Iniciar..."
$menu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\GR7 Presence.lnk'
& $Venv -c "from gr7_presence import autostart as a; from pathlib import Path; a.create_shortcut(Path(r'$menu'))"
if ($LASTEXITCODE -ne 0) { throw "Não consegui criar o atalho no Menu Iniciar." }
Ok "Atalho 'GR7 Presence' criado no Menu Iniciar."
if (Ask "Abrir o GR7 Presence junto com o Windows?") {
    & $Venv -m gr7_presence --autostart on | Out-Null
    Ok "Vai abrir sozinho com o Windows (dá para desligar no menu da bandeja)."
} else {
    & $Venv -m gr7_presence --autostart off | Out-Null
    Ok "Abra pelo Menu Iniciar quando for tocar."
}

Write-Host ""
Write-Host "  Pronto! Abrindo o GR7 Presence na bandeja do sistema (perto do relógio)." -ForegroundColor Green
Write-Host "  Abra o Guitar Rig 7 e confira seu perfil no Discord."
Start-Process -FilePath $VenvW -ArgumentList '-m', 'gr7_presence' -WorkingDirectory $Root
