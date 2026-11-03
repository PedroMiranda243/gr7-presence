"""Aviso de versão nova, pelas releases do repositório no GitHub.

Uma consulta ao abrir e depois uma por dia, em segundo plano. Só lê a página pública da última
release: nada do usuário é enviado. Sem internet ou com o GitHub fora do ar, fica quieto e tenta de
novo no dia seguinte. Desliga com "check_updates": false no config.json.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Callable

from . import REPO, __version__

log = logging.getLogger(__name__)

API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"
CHECK_EVERY = 24 * 3600


@dataclass(frozen=True)
class Release:
    version: str
    url: str


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
    return Release(".".join(map(str, version)), data.get("html_url") or RELEASES_URL)


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
