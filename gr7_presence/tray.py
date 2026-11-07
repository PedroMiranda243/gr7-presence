"""Ícone na bandeja do sistema + janela de estatísticas.

O tkinter fica na thread principal (oculto) e o pystray roda destacado; os cliques do menu
chegam ao tkinter por uma fila, que é lida com root.after.
"""
from __future__ import annotations

import logging
import os
import queue
import threading
import tkinter as tk
from pathlib import Path

import pystray

from . import __version__, app_icon, autostart, updates
from .config import DATA_DIR
from .i18n import Translator
from .main_window import MainWindow
from .settings_page import SettingsPage
from .stats_page import StatsPage
from .update_window import UpdateWindow

log = logging.getLogger(__name__)


class TrayUI:
    def __init__(self, app):
        self.app = app
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("GR7 Presence")
        try:
            self.root.iconbitmap(default=str(app_icon.ICO))   # vale para todas as janelas do programa
        except tk.TclError:
            log.warning("Sem o ícone %s", app_icon.ICO)
        self._queue: queue.Queue = queue.Queue()
        self._main_window: MainWindow | None = None
        self._update_window: UpdateWindow | None = None
        self._notes: list[tuple[str, str]] = []   # (título, texto) esperando o ícone aparecer
        self._images = {True: app_icon.tray_image(True), False: app_icon.tray_image(False)}
        self.icon = pystray.Icon("gr7_presence", self._images[False], "GR7 Presence", menu=self._menu())
        app.on_status = lambda text, active: self._queue.put(("status", text, active))
        app.on_update = lambda release: self._queue.put(("update", release))
        app.on_note = lambda title, body: self._queue.put(("note", title, body))
        if app.updates.available:   # achada antes de a bandeja existir: o aviso não pode se perder
            self._queue.put(("update", app.updates.available))

    def _menu(self) -> pystray.Menu:
        t = lambda key: (lambda _item: self.app.t(key))   # textos seguem o idioma do config
        update = lambda: self.app.updates.available
        return pystray.Menu(
            pystray.MenuItem(lambda _i: self.app.status_text, None, enabled=False),
            pystray.MenuItem(lambda _i: self.app.t("menu_update", version=update().version) if update() else "",
                             lambda: self._queue.put(("update_window",)), visible=lambda _i: update() is not None),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("menu_pause"), self._toggle_pause, checked=lambda _i: self.app.paused),
            pystray.MenuItem(t("menu_stats"), lambda: self._queue.put(("stats",)), default=True),
            pystray.MenuItem(t("menu_config"), lambda: self._queue.put(("settings",))),
            pystray.MenuItem(t("menu_logs"), lambda: os.startfile(DATA_DIR)),
            pystray.MenuItem(t("menu_autostart"), self._toggle_autostart, checked=lambda _i: autostart.is_enabled()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda _i: self.app.t("menu_version", version=__version__), None, enabled=False),
            pystray.MenuItem(t("menu_quit"), lambda: self._queue.put(("quit",))),
        )

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
                    self._notify(self.app.t("update_title", version=version), self.app.t("update_body", version=version))
                elif msg[0] == "update_window":
                    self._show_update()
                elif msg[0] == "update_ready":
                    self._hand_over_to_updater(msg[1], msg[2])
                elif msg[0] == "update_error":
                    if self._update_window:
                        self._update_window.show_error(msg[1])
                elif msg[0] == "stats":
                    self._show_stats()
                elif msg[0] == "settings":
                    self._show_main("settings")
                elif msg[0] == "note":
                    self._notify(msg[1], msg[2])
                elif msg[0] == "quit":
                    self.icon.stop()
                    self.root.quit()
                    return
        except queue.Empty:
            pass
        self._flush_notes()
        self.root.after(250, self._drain)

    def _notify(self, title: str, body: str) -> None:
        self._notes.append((title, body))
        self._flush_notes()

    def _flush_notes(self) -> None:
        # O pystray põe o ícone na bandeja numa thread própria, um instante depois de abrir; até lá
        # uma notificação some sem erro nenhum (a 1.1.0 perdeu assim o aviso da 1.2.0).
        if not self.icon.visible:
            return
        while self._notes:
            title, body = self._notes.pop(0)
            try:
                self.icon.notify(body, title)
            except Exception:   # o item do menu já basta se a notificação falhar
                log.exception("Não consegui mostrar a notificação %r", title)

    def _show_stats(self) -> None:
        self._show_main("stats")

    def _show_main(self, page: str) -> None:
        if self._main_window and self._main_window.alive:
            self._main_window.show(page)
            return
        pages = [StatsPage(self.app.stats, lambda: self.app.config["daily_goal_minutes"]),
                 SettingsPage(self.app.config, self.app.stats, self.app.library, lambda: self.app.last_state)]
        available = lambda: self.app.updates.available.version if self.app.updates.available else None
        # O idioma vem direto do config: mudar nos Ajustes troca a janela na hora, sem esperar o loop.
        self._main_window = MainWindow(self.root, pages, lambda: Translator(self.app.config["language"]), available,
                                       on_update=self._show_update, page=page)

    # ---- atualização com um clique ---------------------------------------------------------
    def _show_update(self) -> None:
        release = self.app.updates.available
        if release is None:
            return
        if self._update_window and self._update_window.alive:
            self._update_window.focus()
            return
        self._update_window = UpdateWindow(self.root, release, __version__, self.app.t,
                                           on_confirm=lambda: self._download(release))

    def _download(self, release: updates.Release) -> None:
        def run():
            try:
                path = updates.download(release)
            except updates.UpdateError as exc:
                log.warning("Atualização não baixada: %s", exc)
                self._queue.put(("update_error", str(exc)))
                return
            self._queue.put(("update_ready", path, release))
        threading.Thread(target=run, name="download", daemon=True).start()

    def _hand_over_to_updater(self, path: Path, release: updates.Release) -> None:
        """O atualizador espera este processo fechar; daqui em diante é com ele."""
        try:
            updates.start_updater(path, release)
        except OSError as exc:
            log.exception("Não consegui iniciar o atualizador")
            if self._update_window:
                self._update_window.show_error(str(exc))
            return
        self._queue.put(("quit",))

    def _announce_last_update(self) -> None:
        result = updates.pop_last_result()
        if not result:
            return
        if result.get("ok"):
            title, body = self.app.t("update_done_title"), self.app.t("update_done_body", version=result.get("para"))
        else:
            title = self.app.t("update_rollback_title")
            body = self.app.t("update_rollback_body", version=result.get("de"), error=result.get("erro") or "?")
        self._notify(title, body)

    def run(self) -> None:
        self.icon.run_detached()
        self.root.after(250, self._drain)
        self.root.after(1000, self._announce_last_update)
        try:
            self.root.mainloop()
        finally:
            try:
                self.icon.stop()
            except Exception:
                pass
