"""Ícone na bandeja do sistema + janela de estatísticas.

O tkinter fica na thread principal (oculto) e o pystray roda destacado; os cliques do menu
chegam ao tkinter por uma fila, que é lida com root.after.
"""
from __future__ import annotations

import logging
import os
import queue
import tkinter as tk
import webbrowser
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from . import __version__, autostart
from .config import CONFIG_PATH, DATA_DIR
from .stats_window import StatsWindow

log = logging.getLogger(__name__)

LOGO = Path(__file__).resolve().parent.parent / "assets" / "discord" / "gr7_logo.png"


def _icon_image(active: bool) -> Image.Image:
    # O logo sai do "Guitar Rig 7.exe" na instalação (tools/make_assets.py --locais) e não vai para o
    # repositório. Sem ele, um círculo na cor do Guitar Rig.
    try:
        base = Image.open(LOGO).convert("RGBA").resize((64, 64), Image.LANCZOS)
    except OSError:
        base = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(base).ellipse((2, 2, 61, 61), fill="#F2572B")
    d = ImageDraw.Draw(base)
    color = "#23A55A" if active else "#80848E"   # verde do Discord / cinza
    d.ellipse((40, 40, 63, 63), fill=color, outline="black", width=3)
    return base


class TrayUI:
    def __init__(self, app):
        self.app = app
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("GR7 Presence")
        self._queue: queue.Queue = queue.Queue()
        self._stats_window: StatsWindow | None = None
        self._images = {True: _icon_image(True), False: _icon_image(False)}
        self.icon = pystray.Icon("gr7_presence", self._images[False], "GR7 Presence", menu=self._menu())
        app.on_status = lambda text, active: self._queue.put(("status", text, active))
        app.on_update = lambda release: self._queue.put(("update", release))

    def _menu(self) -> pystray.Menu:
        t = lambda key: (lambda _item: self.app.t(key))   # textos seguem o idioma do config
        update = lambda: self.app.updates.available
        return pystray.Menu(
            pystray.MenuItem(lambda _i: self.app.status_text, None, enabled=False),
            pystray.MenuItem(lambda _i: self.app.t("menu_update", version=update().version) if update() else "",
                             self._open_update, visible=lambda _i: update() is not None),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("menu_pause"), self._toggle_pause, checked=lambda _i: self.app.paused),
            pystray.MenuItem(t("menu_stats"), lambda: self._queue.put(("stats",)), default=True),
            pystray.MenuItem(t("menu_config"), self._open_config),
            pystray.MenuItem(t("menu_logs"), lambda: os.startfile(DATA_DIR)),
            pystray.MenuItem(t("menu_autostart"), self._toggle_autostart, checked=lambda _i: autostart.is_enabled()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda _i: self.app.t("menu_version", version=__version__), None, enabled=False),
            pystray.MenuItem(t("menu_quit"), lambda: self._queue.put(("quit",))),
        )

    def _open_update(self) -> None:
        if self.app.updates.available:
            webbrowser.open(self.app.updates.available.url)

    # ---- ações do menu (thread do pystray) -----------------------------------------------
    def _toggle_pause(self) -> None:
        self.app.set_paused(not self.app.paused)
        self._queue.put(("status", self.app.t("tray_paused") if self.app.paused else self.app.status_text, False))

    def _toggle_autostart(self) -> None:
        try:
            autostart.set_enabled(not autostart.is_enabled())
        except Exception:
            log.exception("Não consegui mudar o início com o Windows")
        self.icon.update_menu()

    def _open_config(self) -> None:
        if not CONFIG_PATH.exists():
            self.app.config.save()
        os.startfile(CONFIG_PATH)

    # ---- thread principal ----------------------------------------------------------------
    def _drain(self) -> None:
        try:
            while True:
                msg = self._queue.get_nowait()
                if msg[0] == "status":
                    _, text, active = msg
                    self.icon.icon = self._images[bool(active)]
                    self.icon.title = f"GR7 Presence · {text}"[:127]
                    self.icon.update_menu()
                elif msg[0] == "update":
                    version = msg[1].version
                    self.icon.update_menu()
                    try:
                        self.icon.notify(self.app.t("update_body", version=version),
                                         self.app.t("update_title", version=version))
                    except Exception:   # o item do menu já basta se a notificação falhar
                        log.exception("Não consegui mostrar a notificação de versão nova")
                elif msg[0] == "stats":
                    self._show_stats()
                elif msg[0] == "quit":
                    self.icon.stop()
                    self.root.quit()
                    return
        except queue.Empty:
            pass
        self.root.after(250, self._drain)

    def _show_stats(self) -> None:
        if self._stats_window and self._stats_window.alive:
            self._stats_window.focus()
            return
        self._stats_window = StatsWindow(self.root, self.app.stats, self.app.t)

    def run(self) -> None:
        self.icon.run_detached()
        self.root.after(250, self._drain)
        try:
            self.root.mainloop()
        finally:
            try:
                self.icon.stop()
            except Exception:
                pass
