"""O ícone do GR7 Presence (o selo vermelho gerado por tools/icone.py) e a identidade na barra de tarefas.

O programa roda no pythonw.exe. Sem um AppUserModelID próprio, o Windows agrupa as janelas dele sob o
Python e mostra o ícone do Python na barra de tarefas, mesmo com o ícone certo na janela.
"""
from __future__ import annotations

import ctypes
import logging
from pathlib import Path

from PIL import Image, ImageDraw

log = logging.getLogger(__name__)

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ICO = ASSETS / "gr7_presence.ico"
PNG = ASSETS / "gr7_presence.png"
APP_ID = "PedroMiranda243.GR7Presence"


def set_app_id() -> None:
    """Precisa rodar antes da primeira janela existir."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except (AttributeError, OSError) as exc:
        log.debug("Sem AppUserModelID: %s", exc)


def tray_image(active: bool, size: int = 64) -> Image.Image:
    """O pedal com o ponto de status: verde no Discord, cinza esperando."""
    try:
        base = Image.open(PNG).convert("RGBA").resize((size, size), Image.LANCZOS)
    except OSError:   # arquivo apagado: um círculo vermelho no lugar
        base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(base).ellipse((2, 2, size - 3, size - 3), fill="#E0141C")
    d = ImageDraw.Draw(base)
    color = "#23A55A" if active else "#80848E"   # verde do Discord / cinza
    r = size * 0.19
    d.ellipse((size - 2 * r - 1, size - 2 * r - 1, size - 1, size - 1), fill=color, outline="black", width=max(1, size // 21))
    return base
