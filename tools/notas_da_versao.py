"""Confere uma versão antes da release e separa as notas dela no CHANGELOG.md.

    python tools/notas_da_versao.py v1.2.0 --saida notas.md

Falha, e a release não sai, se a tag não tem o formato vX.Y.Z, se não bate com
gr7_presence.__version__ ou se o CHANGELOG.md não tem a seção da versão. É o que impede uma
release cujo programa diz ser outra versão: o aviso de atualização compararia errado.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def package_version() -> str:
    text = (ROOT / "gr7_presence" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__ = "([^"]+)"', text, re.M)
    if not m:
        sys.exit("Não achei __version__ em gr7_presence/__init__.py")
    return m[1]


def release_notes(version: str) -> str:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]: |\Z)", changelog, re.M | re.S)
    if not m or not m[1].strip():
        sys.exit(f"O CHANGELOG.md não tem a seção '## [{version}]' com o que mudou.")
    return m[1].strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", help="a tag da release, ex.: v1.2.0")
    parser.add_argument("--saida", type=Path, help="arquivo onde gravar as notas (UTF-8)")
    args = parser.parse_args()

    if not re.fullmatch(r"v\d+\.\d+\.\d+", args.tag):
        sys.exit(f"A tag '{args.tag}' precisa ser vMAIOR.MENOR.CORREÇÃO, ex.: v1.2.0")
    version = args.tag[1:]
    if package_version() != version:
        sys.exit(f"A tag é {args.tag}, mas gr7_presence/__init__.py diz {package_version()}.")
    notes = release_notes(version)
    if args.saida:
        args.saida.write_text(notes, encoding="utf-8")
        print(f"Versão {version} conferida; notas em {args.saida}")
    else:
        sys.stdout.buffer.write(notes.encode("utf-8"))


if __name__ == "__main__":
    main()
