"""Índice dos presets de rack (.ngrr) de fábrica e do usuário, para achar um preset pelo nome."""
from __future__ import annotations

import ctypes
import difflib
import logging
import threading
import time
from ctypes import wintypes
from pathlib import Path

from .gr7_state import PresetInfo, parse_buffer

log = logging.getLogger(__name__)

FACTORY_DIR = Path(r"C:\Program Files\Common Files\Native Instruments\Guitar Rig 7\Rack Presets")

# Trocas comuns do OCR. Comparamos um "esqueleto" do nome em que elas não fazem diferença.
_OCR_CONFUSIONS = [("rn", "m"), ("vv", "w"), ("yy", "w"), ("1", "i"), ("l", "i"), ("|", "i"), ("!", "i"), ("0", "o")]


def skeleton(text: str) -> str:
    """'AB CTX1' e 'AB CTXI' -> 'abctxi'; 'Auto Rhyth m' -> 'autorhythm'."""
    out = "".join(ch for ch in text.lower() if ch.isalnum() or ch in "&|!")
    for wrong, right in _OCR_CONFUSIONS:
        out = out.replace(wrong, right)
    return out


def documents_dir() -> Path:
    """Pasta Documentos real (pode estar redirecionada para o OneDrive)."""
    buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:   # CSIDL_PERSONAL
        return Path(buf.value)
    return Path.home() / "Documents"


def user_dirs() -> list[Path]:
    """Onde o Guitar Rig 7 salva e importa os presets do usuário (manual, "Importing User Presets")."""
    return [documents_dir() / "Native Instruments" / "User Content" / "Guitar Rig 7"]


class PresetLibrary:
    MATCH_CUTOFF = 0.86
    RESCAN_SECONDS = 30.0   # de quanto em quanto tempo confere se as pastas do usuário mudaram

    def __init__(self, factory_dir: Path = FACTORY_DIR, extra_dirs: list[Path] | None = None):
        self.factory_dir = Path(factory_dir)
        self.extra_dirs = [Path(d) for d in (extra_dirs if extra_dirs is not None else user_dirs())]
        self._index: dict[str, tuple[str, Path, bool]] | None = None   # minúsculo -> (nome, arquivo, de fábrica)
        self._skeletons: dict[str, str] = {}                              # esqueleto -> chave do índice
        self._cache: dict[str, PresetInfo | None] = {}
        self._lock = threading.Lock()
        self._signature: tuple = ()
        self._checked_at = 0.0

    def _user_signature(self) -> tuple:
        """Data de modificação das pastas do usuário e das subpastas: muda quando um preset é
        salvo, importado, copiado, renomeado ou apagado."""
        out = []
        for folder in self.extra_dirs:
            try:
                out.append((str(folder), folder.stat().st_mtime))
                for sub in folder.rglob("*"):
                    if sub.is_dir():
                        out.append((str(sub), sub.stat().st_mtime))
            except OSError:
                out.append((str(folder), None))
        return tuple(out)

    def _build(self) -> dict[str, tuple[str, Path, bool]]:
        index: dict[str, tuple[str, Path, bool]] = {}
        sources = [(self.factory_dir, True)] + [(d, False) for d in self.extra_dirs]
        for folder, factory in sources:
            try:
                # Pastas mais rasas primeiro: "Rack Presets/X.ngrr" ganha de "Rack Presets/LE/.../X.ngrr".
                for path in sorted(folder.rglob("*.ngrr"), key=lambda p: len(p.parts)):
                    index.setdefault(path.stem.lower(), (path.stem, path, factory))
            except OSError as exc:
                log.debug("Não consegui listar %s: %s", folder, exc)
        log.info("Biblioteca de presets: %d presets", len(index))
        return index

    @property
    def index(self) -> dict[str, tuple[str, Path, bool]]:
        with self._lock:
            now = time.monotonic()
            if self._index is not None and now - self._checked_at >= self.RESCAN_SECONDS:
                self._checked_at = now
                if self._user_signature() != self._signature:
                    log.info("Presets do usuário mudaram; relendo a biblioteca")
                    self._index = None
                    self._cache.clear()
            if self._index is None:
                self._signature = self._user_signature()
                self._checked_at = now
                self._index = self._build()
                self._skeletons = {}
                for key in self._index:
                    self._skeletons.setdefault(skeleton(key), key)
            return self._index

    def refresh(self) -> None:
        with self._lock:
            self._index = None
            self._cache.clear()

    def match(self, text: str) -> tuple[str, float] | None:
        """Nome do preset mais parecido com `text` (texto do OCR) e a semelhança (0..1)."""
        key = " ".join(text.split()).strip(" *•·-").lower()
        index = self.index
        if key in index:
            return index[key][0], 1.0
        if key.endswith(("...", "…")):
            return self._match_truncated(key.rstrip(".… "))
        sk = skeleton(key)
        if len(sk) < 2:
            return None
        if sk in self._skeletons:
            return index[self._skeletons[sk]][0], 0.99
        best = difflib.get_close_matches(sk, self._skeletons.keys(), n=1, cutoff=self.MATCH_CUTOFF)
        if not best:
            return None
        return index[self._skeletons[best[0]]][0], difflib.SequenceMatcher(None, sk, best[0]).ratio()

    def _match_truncated(self, start: str) -> tuple[str, float] | None:
        """Nome longo cortado pelo Guitar Rig ("ABCD - Post Punk Lead 6 (R..."): procura o preset
        cujo começo bate com o texto, tolerando erros de OCR. Só aceita se não houver empate."""
        sk = skeleton(start)
        if len(sk) < 6:
            return None
        scored = sorted(((difflib.SequenceMatcher(None, sk, s[:len(sk)]).ratio(), k)
                         for s, k in self._skeletons.items() if len(s) > len(sk)), reverse=True)
        if not scored or scored[0][0] < self.MATCH_CUTOFF:
            return None
        if len(scored) > 1 and scored[1][0] == scored[0][0]:
            return None   # dois presets começam igual: melhor não chutar
        return self._index[scored[0][1]][0], scored[0][0]

    def load(self, name: str) -> PresetInfo | None:
        key = name.lower()
        if key in self._cache:
            return self._cache[key]
        entry = self.index.get(key)
        info = None
        if entry:
            try:
                info = parse_buffer(entry[1].read_bytes())
            except OSError as exc:
                log.warning("Não consegui ler %s: %s", entry[1], exc)
            if info is not None:
                info.name = info.name or entry[0]
                info.is_factory = entry[2]
        self._cache[key] = info
        return info
