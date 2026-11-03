"""Traz config e estatísticas das versões antigas, que guardavam tudo em %APPDATA%\\GR7 Presence.

Pode haver duas cópias antigas: a pasta de verdade e a cópia privada que o Windows cria em
%LOCALAPPDATA%\\Packages\\<app>\\LocalCache\\Roaming quando o programa é aberto de dentro de um app
empacotado (MSIX). As sessões das duas são juntadas, sem repetir.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from .config import DATA_DIR

log = logging.getLogger(__name__)


def legacy_dirs() -> list[Path]:
    dirs = [Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "GR7 Presence"]
    packages = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Packages"
    try:
        dirs += sorted(packages.glob("*/LocalCache/Roaming/GR7 Presence"))
    except OSError:
        pass
    return [d for d in dirs if d.is_dir()]


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def migrate(data_dir: Path = DATA_DIR, sources: list[Path] | None = None) -> bool:
    """Copia os dados antigos para `data_dir` uma única vez (se ainda não houver config lá)."""
    data_dir = Path(data_dir)
    if (data_dir / "config.json").exists():
        return False
    sources = legacy_dirs() if sources is None else [Path(s) for s in sources]
    if not sources:
        return False
    data_dir.mkdir(parents=True, exist_ok=True)

    # config: a mais recente que tenha o Application ID (senão, a mais recente)
    configs = [(_mtime(d / "config.json"), cfg) for d in sources
               if isinstance(cfg := _read_json(d / "config.json"), dict)]
    with_id = [c for c in configs if str(c[1].get("client_id", "")).strip()]
    if configs:
        _, cfg = max(with_id or configs, key=lambda c: c[0])
        (data_dir / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    # estatísticas: todas as sessões, sem repetir (a mesma sessão pode estar nas duas cópias)
    sessions: dict[tuple, dict] = {}
    for d in sources:
        data = _read_json(d / "stats.json")
        for s in (data or {}).get("sessions", []) if isinstance(data, dict) else []:
            if not isinstance(s, dict):
                continue
            key = (round(float(s.get("start", 0)), 1), s.get("mode"))
            if key not in sessions or s.get("seconds", 0) > sessions[key].get("seconds", 0):
                sessions[key] = s
    if sessions:
        payload = {"version": 1, "sessions": sorted(sessions.values(), key=lambda s: s.get("start", 0))}
        (data_dir / "stats.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    # último preset lido: o mais recente
    states = [d / "live_state.json" for d in sources if (d / "live_state.json").exists()]
    if states:
        shutil.copy2(max(states, key=_mtime), data_dir / "live_state.json")

    log.info("Dados antigos trazidos de %s (%d sessões)", ", ".join(str(s) for s in sources), len(sessions))
    return True
