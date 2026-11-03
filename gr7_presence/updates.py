"""Versão nova pelas releases do repositório no GitHub: aviso e atualização com um clique.

Uma consulta ao abrir e depois uma por dia, em segundo plano. Só lê a página pública da última
release: nada do usuário é enviado. Sem internet ou com o GitHub fora do ar, fica quieto e tenta de
novo no dia seguinte. Desliga com "check_updates": false no config.json.

Atualizar só acontece quando a pessoa confirma. O zip vem do anexo da release e é conferido pelo
sha256 que a API do GitHub informa; quem troca os arquivos é o tools/atualizar.py, rodando sozinho
depois que o programa fecha (ver a decisão D7 em docs/decisoes.md).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import REPO, __version__
from .autostart import pythonw
from .config import DATA_DIR, PROJECT_DIR

log = logging.getLogger(__name__)

API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"
# O link do zip vem da API, mas só é seguido se for de uma release deste repositório.
DOWNLOAD_PREFIX = f"https://github.com/{REPO}/releases/download/"
ASSET_NAME = "GR7-Presence.zip"
CHECK_EVERY = 24 * 3600
UPDATER = PROJECT_DIR / "tools" / "atualizar.py"
WORK_DIR = Path(tempfile.gettempdir()) / "GR7 Presence atualizacao"
RESULT_PATH = DATA_DIR / "atualizacao.json"   # escrito pelo tools/atualizar.py


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    zip_url: str | None = None
    sha256: str | None = None
    notes: str = ""


class UpdateError(Exception):
    """Falha ao baixar ou conferir a atualização; a mensagem vai para quem usa."""


def parse_version(text: str) -> tuple[int, int, int] | None:
    """'v1.2.3' ou '1.2.3' -> (1, 2, 3). Qualquer outra coisa (pré-release, lixo) -> None."""
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", (text or "").strip())
    return (int(m[1]), int(m[2]), int(m[3])) if m else None


def is_newer(candidate: str, current: str) -> bool:
    new, old = parse_version(candidate), parse_version(current)
    return new is not None and old is not None and new > old


def fetch_latest(opener=urllib.request.urlopen, timeout: float = 10) -> Release | None:
    request = urllib.request.Request(API_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"GR7-Presence/{__version__}",
    })
    try:
        with opener(request, timeout=timeout) as response:
            data = json.load(response)
    except (OSError, ValueError) as exc:   # sem internet, GitHub fora, resposta estranha
        log.debug("Não consegui consultar as releases: %s", exc)
        return None
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    version = parse_version(data.get("tag_name", ""))
    if version is None:
        return None
    asset = next((a for a in data.get("assets") or [] if isinstance(a, dict) and a.get("name") == ASSET_NAME), {})
    digest = asset.get("digest") or ""
    return Release(".".join(map(str, version)), data.get("html_url") or RELEASES_URL,
                   zip_url=asset.get("browser_download_url"),
                   sha256=digest[7:].lower() if digest.startswith("sha256:") else None,
                   notes=data.get("body") or "")


def download(release: Release, folder: Path = WORK_DIR, opener=urllib.request.urlopen, timeout: float = 60) -> Path:
    """Baixa o zip da release e confere o sha256. Arquivo que não confere é apagado, nunca usado."""
    if not release.zip_url or not release.sha256:
        raise UpdateError("a versão nova não traz o zip com o código de conferência")
    if not release.zip_url.startswith(DOWNLOAD_PREFIX):
        raise UpdateError("o link do zip não é do repositório do GR7 Presence")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"GR7-Presence-{release.version}.zip"
    partial = target.with_name(target.name + ".parcial")
    digest = hashlib.sha256()
    request = urllib.request.Request(release.zip_url, headers={"User-Agent": f"GR7-Presence/{__version__}"})
    try:
        with opener(request, timeout=timeout) as response, partial.open("wb") as out:
            while chunk := response.read(64 * 1024):
                digest.update(chunk)
                out.write(chunk)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        raise UpdateError(f"não consegui baixar ({exc})") from exc
    if digest.hexdigest() != release.sha256:
        partial.unlink(missing_ok=True)
        raise UpdateError("o arquivo baixado não confere com o da versão publicada")
    os.replace(partial, target)
    log.info("Versão %s baixada e conferida: %s", release.version, target)
    return target


def start_updater(zip_path: Path, release: Release, current: str = __version__, project_dir: Path = PROJECT_DIR,
                  python: Path | None = None, pid: int | None = None, folder: Path = WORK_DIR) -> None:
    """Deixa o atualizador rodando sozinho. Ele espera este processo (`pid`) fechar antes de mexer em
    qualquer arquivo. Vai uma cópia para fora da pasta do programa: quem troca os arquivos é o
    atualizador desta versão, que já está instalada e testada, e não o que vem no zip."""
    folder.mkdir(parents=True, exist_ok=True)
    script = folder / "atualizar.py"
    shutil.copy2(UPDATER, script)
    args = [str(python or pythonw()), str(script), "--raiz", str(project_dir), "--zip", str(zip_path),
            "--versao", release.version, "--versao-atual", current, "--esperar-pid", str(pid or os.getpid())]
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(args, cwd=folder, creationflags=flags, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log.info("Atualizador iniciado para a versão %s", release.version)


def pop_last_result(path: Path = RESULT_PATH) -> dict | None:
    """O que o atualizador deixou da última vez (uma vez só: o arquivo é apagado ao ler)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        path.unlink()
    except OSError:
        pass
    return data if isinstance(data, dict) else None


class UpdateChecker:
    def __init__(self, current: str = __version__, fetch: Callable[[], Release | None] = fetch_latest,
                 clock: Callable[[], float] = time.time):
        self.current = current
        self.available: Release | None = None
        self._fetch = fetch
        self._clock = clock
        self._last_check: float | None = None
        self._busy = threading.Lock()

    def due(self) -> bool:
        return self._last_check is None or self._clock() - self._last_check >= CHECK_EVERY

    def check(self) -> Release | None:
        """Consulta agora. Devolve a release só na primeira vez que acha uma versão mais nova que
        esta: o aviso aparece uma vez, e o item do menu fica até a pessoa atualizar."""
        if not self._busy.acquire(blocking=False):
            return None
        try:
            self._last_check = self._clock()
            release = self._fetch()
            if release is None or not is_newer(release.version, self.current) or release == self.available:
                return None
            log.info("Versão nova disponível: %s (esta é %s)", release.version, self.current)
            self.available = release
            return release
        finally:
            self._busy.release()

    def check_in_background(self, on_found: Callable[[Release], None]) -> None:
        def run():
            release = self.check()
            if release:
                on_found(release)
        self._last_check = self._clock()   # não dispara outra consulta enquanto esta roda
        threading.Thread(target=run, name="updates", daemon=True).start()
