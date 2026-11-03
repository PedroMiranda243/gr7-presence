"""Atalho na pasta Inicializar do Windows (shell:startup)."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from .app_icon import ICO as ICON

log = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).resolve().parent.parent
PROGRAMS_DIR = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
STARTUP_DIR = PROGRAMS_DIR / "Startup"
SHORTCUT = STARTUP_DIR / "GR7 Presence.lnk"
MENU_SHORTCUT = PROGRAMS_DIR / "GR7 Presence.lnk"


def pythonw() -> Path:
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return candidate if candidate.exists() else exe


def create_shortcut(path: Path, description: str = "Discord Rich Presence para o Guitar Rig 7") -> None:
    """Cria um .lnk que roda `pythonw -m gr7_presence` sem janela de console."""
    path.parent.mkdir(parents=True, exist_ok=True)

    def q(value) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut(" + q(path) + ");"
        f"$s.TargetPath = {q(pythonw())};"
        "$s.Arguments = '-m gr7_presence';"
        f"$s.WorkingDirectory = {q(PROJECT_DIR)};"
        f"$s.IconLocation = {q(ICON if ICON.exists() else pythonw())};"
        f"$s.Description = {q(description)};"
        "$s.WindowStyle = 7;"
        "$s.Save()"
    )
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                   check=True, capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def is_enabled() -> bool:
    return SHORTCUT.exists()


def refresh_shortcuts(paths: tuple[Path, ...] = (MENU_SHORTCUT, SHORTCUT), create=None) -> list[Path]:
    """Recria os atalhos que já existem, para pegarem o ícone atual. Usado na atualização: um
    atalho que a pessoa apagou (ou o início com o Windows desligado) continua não existindo."""
    create = create or create_shortcut
    done = []
    for path in paths:
        if path.exists():
            create(path)
            done.append(path)
    return done


def set_enabled(enabled: bool) -> None:
    if enabled:
        create_shortcut(SHORTCUT)
        log.info("Início com o Windows ligado (%s)", SHORTCUT)
    elif SHORTCUT.exists():
        SHORTCUT.unlink()
        log.info("Início com o Windows desligado")
