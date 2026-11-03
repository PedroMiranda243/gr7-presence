"""Aplica uma atualização do GR7 Presence. Roda sozinho, depois que o programa fecha.

O programa (gr7_presence/updates.py) baixa o zip da release, confere o sha256 e roda uma cópia
deste script tirada da versão instalada, de fora da pasta do programa:

1. espera o programa fechar. Enquanto ele roda, os .pyd do psutil e do Pillow ficam presos, e o pip
   não conseguiria atualizá-los;
2. confere o zip: estrutura, versão, nenhum caminho fora da pasta, nada em dados\\ nem em .venv\\;
3. guarda uma cópia dos arquivos que vão ser trocados e extrai os novos por cima;
4. roda tools\\instalar.ps1 -Atualizacao: dependências, ícone, e abre o programa;
5. se qualquer passo falhar, devolve os arquivos antigos e abre a versão anterior.

O resultado vai para dados\\atualizacao.json (o programa avisa na próxima abertura) e o passo a passo
para dados\\atualizacao.log. Só usa a biblioteca padrão: as bibliotecas do ambiente Python podem estar
sendo atualizadas pelo pip enquanto este script roda.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath

TOP = "GR7 Presence/"          # pasta de dentro do zip (tools/empacotar.py)
PROTECTED = {"dados", ".venv"}  # o que é de quem usa e nunca vem no zip
WAIT_SECONDS = 60
INSTALL_TIMEOUT = 900
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DETACHED = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


class UpdateFailed(Exception):
    pass


class Log:
    def __init__(self, root: Path):
        self.path = root / "dados" / "atualizacao.log"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, text: str) -> None:
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {text}"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")


def wait_for_exit(pid: int, timeout: float = WAIT_SECONDS) -> bool:
    """True quando o processo já fechou (ou nunca existiu)."""
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel32.OpenProcess(0x00100000, False, pid)   # SYNCHRONIZE
    if not handle:
        return True
    try:
        return kernel32.WaitForSingleObject(handle, int(timeout * 1000)) == 0   # WAIT_OBJECT_0
    finally:
        kernel32.CloseHandle(handle)


def package_files(archive: zipfile.ZipFile, version: str) -> dict[str, zipfile.ZipInfo]:
    """Arquivos do zip -> caminho relativo na pasta do programa. Um único arquivo fora do lugar
    recusa o zip inteiro: nada é extraído pela metade."""
    files: dict[str, zipfile.ZipInfo] = {}
    for info in archive.infolist():
        if info.is_dir():
            continue
        name = info.filename.replace("\\", "/")
        if not name.startswith(TOP):
            raise UpdateFailed(f"arquivo fora da pasta '{TOP.rstrip('/')}' no zip: {name}")
        rel = PurePosixPath(name[len(TOP):])
        if not rel.parts or rel.is_absolute() or ".." in rel.parts or ":" in rel.parts[0]:
            raise UpdateFailed(f"caminho inválido no zip: {name}")
        if rel.parts[0].lower() in PROTECTED:
            raise UpdateFailed(f"o zip tenta mexer em {rel.parts[0]}\\: {name}")
        files[rel.as_posix()] = info
    init = files.get("gr7_presence/__init__.py")
    if init is None:
        raise UpdateFailed("o zip não tem gr7_presence/__init__.py")
    if f'__version__ = "{version}"' not in archive.read(init).decode("utf-8", "replace"):
        raise UpdateFailed(f"o zip não é da versão {version}")
    return files


def apply(root: Path, archive: zipfile.ZipFile, files: dict[str, zipfile.ZipInfo], backup: Path) -> None:
    """Guarda em `backup` os arquivos que vão ser trocados (e a lista dos que não existiam) e só
    depois extrai os novos."""
    if backup.exists():
        shutil.rmtree(backup)
    saved = backup / "arquivos"
    saved.mkdir(parents=True)
    created = []
    for rel in files:
        target = root / rel
        if target.exists():
            (saved / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved / rel)
        else:
            created.append(rel)
    (backup / "novos.json").write_text(json.dumps(created), encoding="utf-8")
    for rel, info in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".novo")
        tmp.write_bytes(archive.read(info))
        os.replace(tmp, target)


def rollback(root: Path, backup: Path) -> None:
    """Devolve os arquivos guardados por apply() e apaga os que a versão nova criou."""
    saved = backup / "arquivos"
    if saved.exists():
        for src in saved.rglob("*"):
            if src.is_file():
                dest = root / src.relative_to(saved)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
    try:
        created = json.loads((backup / "novos.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        created = []
    for rel in created:
        (root / rel).unlink(missing_ok=True)


def run_installer(root: Path) -> tuple[int, str]:
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(root / "tools" / "instalar.ps1"), "-Atualizacao"],
        cwd=root, capture_output=True, timeout=INSTALL_TIMEOUT, creationflags=NO_WINDOW)
    # O PowerShell 5.1 escreve no pipe com a página de código do console.
    output = (proc.stdout + proc.stderr).decode("oem" if os.name == "nt" else "utf-8", "replace")
    return proc.returncode, output


def start_program(root: Path) -> None:
    python = root / ".venv" / "Scripts" / "pythonw.exe"
    subprocess.Popen([str(python), "-m", "gr7_presence"], cwd=root, creationflags=DETACHED, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def update(root: Path, zip_path: Path, version: str, current: str, pid: int | None, *,
           installer=run_installer, starter=start_program, wait=wait_for_exit) -> dict:
    log = Log(root)
    result = {"de": current, "para": version, "ok": False, "erro": None, "quando": time.strftime("%Y-%m-%d %H:%M:%S")}
    backup = root / "dados" / "atualizacao" / "anterior"
    touched = False
    log(f"Atualizando de {current} para {version} com {zip_path}")
    try:
        if pid and not wait(pid, WAIT_SECONDS):
            raise UpdateFailed("o GR7 Presence não fechou a tempo")
        with zipfile.ZipFile(zip_path) as archive:
            if archive.testzip() is not None:
                raise UpdateFailed("o zip está corrompido")
            files = package_files(archive, version)
            touched = True   # daqui em diante pode haver arquivo trocado
            apply(root, archive, files, backup)
        log(f"{len(files)} arquivos trocados; cópia dos antigos em {backup}")
        code, output = installer(root)
        log("Instalador:\n" + output.strip())
        if code != 0:
            raise UpdateFailed(f"o instalador terminou com erro (código {code})")
        result["ok"] = True
        log(f"Pronto: versão {version} instalada")
    except Exception as exc:   # roda sem ninguém olhando: qualquer erro volta para a versão que funcionava
        result["erro"] = str(exc) or type(exc).__name__
        log(f"Falhou: {result['erro']}")
        if touched:
            try:
                rollback(root, backup)
                log(f"Arquivos da versão {current} devolvidos")
            except Exception as again:
                log(f"Não consegui devolver os arquivos: {again}")
        try:
            starter(root)
        except Exception as again:
            log(f"Não consegui reabrir o programa: {again}")
    finally:
        try:
            (root / "dados" / "atualizacao.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            log(f"Não consegui gravar o resultado: {exc}")
        Path(zip_path).unlink(missing_ok=True)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aplica uma atualização do GR7 Presence")
    parser.add_argument("--raiz", type=Path, required=True, help="pasta do programa")
    parser.add_argument("--zip", type=Path, required=True, help="zip da release, já conferido")
    parser.add_argument("--versao", required=True, help="versão do zip")
    parser.add_argument("--versao-atual", required=True, help="versão instalada agora")
    parser.add_argument("--esperar-pid", type=int, help="processo do programa, que precisa fechar antes")
    args = parser.parse_args(argv)
    result = update(args.raiz.resolve(), args.zip, args.versao, args.versao_atual, args.esperar_pid)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
