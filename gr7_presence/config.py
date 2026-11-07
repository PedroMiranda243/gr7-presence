"""Configuração em <pasta do projeto>\\dados\\config.json, com recarga ao vivo.

Os dados ficam na pasta do projeto, e não em %APPDATA%: programas abertos de dentro de um app
empacotado (MSIX, como o app desktop do Claude) têm o AppData redirecionado para uma cópia
privada, e o GR7 Presence aberto pelo Menu Iniciar não enxergaria essa cópia.
"""
from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

APP_NAME = "GR7 Presence"
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "dados"
CONFIG_PATH = DATA_DIR / "config.json"
STATS_PATH = DATA_DIR / "stats.json"
LOG_PATH = DATA_DIR / "gr7_presence.log"

DEFAULTS: dict = {
    # Application ID do app "Guitar Rig 7" no Discord Developer Portal.
    "client_id": "1564119765943984278",
    # "pt" ou "en"
    "language": "pt",
    # Segundos entre um cartão e outro (mínimo 15 por causa do limite do Discord).
    "rotate_seconds": 20,
    # "playing" (Jogando), "listening" (Ouvindo), "watching" (Assistindo) ou "competing" (Competindo)
    "activity_type": "playing",
    # O que aparece na lista de membros: "name" (Guitar Rig 7), "details" (linha 1) ou "state" (linha 2)
    "status_display": "name",
    "show_preset": True,
    "show_rack_chain": True,
    "show_tags": True,
    "show_backing_track": True,
    "show_stats": True,
    "show_streak": True,
    # Meta diária de prática, em minutos (0 = sem meta). Aparece nas Estatísticas.
    "daily_goal_minutes": 30,
    # Notificação do Windows quando a meta do dia é batida.
    "notify_goal": True,
    # Notificação do Windows quando o Guitar Rig é minimizado (uma por vez que ele é aberto).
    "notify_minimized": True,
    # A janela de primeira abertura já apareceu (ela aparece uma vez, depois de instalar).
    "welcome_done": False,
    # Detecta o Guitar Rig 7 como plugin VST3 dentro de uma DAW (REAPER, FL Studio, Ableton...).
    "detect_plugin_hosts": True,
    # Uma vez por dia, confere no GitHub se saiu versão nova do GR7 Presence e avisa na bandeja.
    "check_updates": True,
    # Até 2 botões; só outras pessoas os veem. Deixe "url" vazio para esconder.
    "buttons": [
        {"label": "Conhecer o Guitar Rig 7", "url": "https://www.native-instruments.com/en/products/komplete/guitar/guitar-rig-7-pro/"},
        {"label": "", "url": ""},
    ],
    # Chaves das imagens enviadas em Rich Presence > Art Assets.
    "assets": {
        "logo": "gr7_logo",
        "amp": "amp",
        "pedal": "pedal",
        "tape": "tape",
        "clock": "clock",
        "fire": "fire",
        "daw": "daw",
    },
}


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


class Config:
    def __init__(self, path: Path = CONFIG_PATH):
        self.path = Path(path)
        self._mtime: float | None = None
        self.data: dict = copy.deepcopy(DEFAULTS)
        self.load()

    def __getitem__(self, key: str):
        return self.data.get(key, DEFAULTS.get(key))

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def load(self) -> None:
        if not self.path.exists():
            self.save()
            return
        try:
            user = json.loads(self.path.read_text(encoding="utf-8-sig"))
            if not isinstance(user, dict):
                raise ValueError("o arquivo precisa ser um objeto JSON")
            obsolete = [k for k in user if k not in DEFAULTS]
            for key in obsolete:   # opções de versões antigas
                user.pop(key)
            self.data = _merge(DEFAULTS, user)
            if obsolete:
                self.save()
        except (OSError, ValueError) as exc:
            log.error("config.json inválido (%s); mantendo a configuração anterior", exc)
        self._mtime = self._stat()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)
        self._mtime = self._stat()

    def set(self, key: str, value) -> None:
        self.data[key] = value
        self.save()

    def update(self, key: str, value) -> None:
        """Muda uma opção pela janela de Ajustes. Grava e faz o loop recarregar o arquivo na próxima
        volta, como se a pessoa tivesse editado o config.json: assim ele reaplica o idioma, a detecção
        de DAWs e reenvia o cartão."""
        self.data[key] = value
        self.save()
        self._mtime = None

    def reload_if_changed(self) -> bool:
        mtime = self._stat()
        if mtime is not None and mtime != self._mtime:
            self.load()
            log.info("config.json recarregado")
            return True
        return False

    def _stat(self) -> float | None:
        try:
            return self.path.stat().st_mtime
        except OSError:
            return None
