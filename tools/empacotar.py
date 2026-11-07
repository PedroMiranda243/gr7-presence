"""Gera dist\\GR7-Presence.zip, o pacote anexado a cada release do GitHub.

    .venv\\Scripts\\python tools\\empacotar.py              # confere e gera o zip
    .venv\\Scripts\\python tools\\empacotar.py --verificar  # só confere (a CI roda em todo PR)

O zip leva só arquivos versionados no git (`git ls-files`). O que o .gitignore deixa de fora não tem
como entrar: .venv, dados\\ (config, estatísticas, log), o ícone oficial do Guitar Rig que a
instalação gera, os presets pessoais. Os testes também ficam de fora: quem desenvolve clona o
repositório.

Antes de tudo, procura dados pessoais em todos os arquivos versionados:
- caminhos de usuário do Windows (C:\\Users\\<nome>), menos os nomes de exemplo;
- as palavras de uma lista privada, que não pode morar no repositório público: a variável de
  ambiente GR7_PALAVRAS_PRIVADAS (um secret do GitHub Actions, palavras separadas por vírgula) ou o
  arquivo dados\\palavras-privadas.txt (uma por linha). Com --exigir-palavras, falta de lista é erro:
  a release nunca sai sem essa conferência.
"""
from __future__ import annotations

import fnmatch
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "GR7-Presence.zip"
TOP = "GR7 Presence"   # pasta que aparece ao extrair

INCLUDE = [
    "instalar.bat", "desinstalar.bat", "COMO INSTALAR.txt", "README.md", "LICENSE", "CHANGELOG.md",
    "requirements.txt", "requirements-ocr.txt",
    "gr7_presence/*.py", "tools/*.py", "tools/*.ps1", "assets/discord/*.png",
    "assets/gr7_presence.ico", "assets/gr7_presence.png",
    "assets/fonts/Archivo.ttf", "assets/fonts/OFL.txt",   # a fonte da interface e a licença dela
]
# Só servem para quem publica uma versão.
EXCLUDE = {"tools/empacotar.py", "tools/notas_da_versao.py"}
BINARY = {".png", ".ico", ".ttf", ".zip", ".ngrr", ".tle"}
PRIVATE_FILE = ROOT / "dados" / "palavras-privadas.txt"
USER_PATH = re.compile(r"(?i)\b[a-z]:[\\/]+users[\\/]+([^\\/\s\"'<>`]+)")
EXAMPLE_USERS = {"x", "public", "default", "voce", "você", "usuario", "usuário"}


def tracked() -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        sys.exit(f"Preciso do git e de um clone do repositório: {exc}")
    return sorted(p for p in out.decode("utf-8").split("\0") if p)


def private_words() -> list[str]:
    words = re.split(r"[,\n]", os.environ.get("GR7_PALAVRAS_PRIVADAS", ""))
    if PRIVATE_FILE.exists():
        words += PRIVATE_FILE.read_text(encoding="utf-8-sig").splitlines()
    return sorted({w.strip().lower() for w in words if w.strip()})


def personal_data(files: list[str], words: list[str]) -> list[str]:
    problems = []
    for rel in files:
        if Path(rel).suffix.lower() in BINARY:
            continue
        text = (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")
        for m in USER_PATH.finditer(text):
            if m.group(1).lower() not in EXAMPLE_USERS:
                problems.append(f"{rel}: caminho de usuário '{m.group(0)}'")
        lower = text.lower()
        # A palavra em si não aparece na saída: o log da CI é público.
        problems += [f"{rel}: palavra nº {i + 1} da lista privada" for i, w in enumerate(words) if w in lower]
    return problems


def package_files(files: list[str]) -> list[str]:
    chosen = [f for f in files if any(fnmatch.fnmatch(f, p) for p in INCLUDE) and f not in EXCLUDE]
    missing = [p for p in INCLUDE if not any(fnmatch.fnmatch(f, p) for f in chosen)]
    if missing:
        sys.exit("Faltou no repositório: " + ", ".join(missing))
    return chosen


def main() -> None:
    files = tracked()
    words = private_words()
    if not words:
        if "--exigir-palavras" in sys.argv:
            sys.exit("Lista de palavras privadas vazia: configure o secret GR7_PALAVRAS_PRIVADAS.")
        print("Aviso: sem lista de palavras privadas; conferindo só os caminhos de usuário.")
    problems = personal_data(files, words)
    if problems:
        sys.exit("Dados pessoais no repositório:\n  " + "\n  ".join(problems))
    print(f"OK: nenhum dado pessoal em {len(files)} arquivos versionados ({len(words)} palavras privadas).")
    if "--verificar" in sys.argv:
        return

    chosen = package_files(files)
    OUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in chosen:
            zf.write(ROOT / rel, f"{TOP}/{rel}")
    print(f"{OUT}  ({len(chosen)} arquivos, {OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
