"""Ícone na bandeja do sistema, o menu, os avisos e as janelas do programa.

O tkinter fica na thread principal (oculto) e o pystray roda destacado; os cliques do menu
chegam ao tkinter por uma fila, que é lida com root.after.

O menu é curto (direção "Palco"): o que se usa sem abrir nada. Estatísticas, ajustes, registros e
"Iniciar com o Windows" ficam dentro da janela.
"""
from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path

import pystray

from . import __version__, app_icon, updates
from .dashboard_page import DashboardPage
from .i18n import Translator
from .main_window import MainWindow
from .settings_page import SettingsPage
from .stats_page import StatsPage
from .update_page import UpdatePage
from .welcome_page import SIZE as WELCOME_SIZE
from .welcome_page import WelcomePage

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
        self._welcome: MainWindow | None = None
        self._update_page: UpdatePage | None = None
        self._notes: list[tuple[str, str]] = []   # (título, texto) esperando o ícone aparecer
        self._images = {True: app_icon.tray_image(True), False: app_icon.tray_image(False)}
        self.icon = pystray.Icon("gr7_presence", self._images[False], "GR7 Presence", menu=self._menu())
        app.on_status = lambda text, active: self._queue.put(("status", text, active))
        app.on_update = lambda release: self._queue.put(("update", release))
        app.on_note = lambda title, body: self._queue.put(("note", title, body))
        if app.updates.available:   # achada antes de a bandeja existir: o aviso não pode se perder
            self._queue.put(("update", app.updates.available))

    def t(self, key: str, **kwargs) -> str:
        return Translator(self.app.config["language"])(key, **kwargs)

    def _menu(self) -> pystray.Menu:
        text = lambda key: (lambda _item: self.t(key))   # textos seguem o idioma do config
        update = lambda: self.app.updates.available
        paused = lambda _i: self.app.paused
        return pystray.Menu(
            pystray.MenuItem(lambda _i: self.app.status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(text("menu_open"), lambda: self._queue.put(("open", "dashboard")), default=True),
            pystray.MenuItem(text("menu_pause_hour"), lambda: self._pause(3600), visible=lambda _i: not self.app.paused),
            pystray.MenuItem(text("menu_pause_forever"), lambda: self._pause(None), visible=lambda _i: not self.app.paused),
            pystray.MenuItem(text("menu_resume"), self._resume, visible=paused),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda _i: self.t("menu_update", version=update().version) if update() else "",
                             lambda: self._queue.put(("open", "update")), visible=lambda _i: update() is not None),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(text("menu_quit"), lambda: self._queue.put(("quit",))),
        )

    # ---- ações do menu (thread do pystray) -----------------------------------------------
    def _pause(self, seconds: float | None) -> None:
        self.app.set_paused(True, seconds)
        self._queue.put(("status", self.t("tray_paused"), False))

    def _resume(self) -> None:
        self.app.set_paused(False)
        self._queue.put(("status", self.app.status_text, False))

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
                    self._notify(self.t("update_title", version=version), self.t("update_body", version=version))
                    if self._main_window and self._main_window.alive:
                        self._main_window.render_rail()   # o item da versão nova aparece no pé da barra
                elif msg[0] == "open":
                    self._show_main(msg[1])
                elif msg[0] == "update_progress":
                    if self._update_page:
                        self._update_page.set_progress(msg[1], msg[2])
                elif msg[0] == "update_ready":
                    self._hand_over_to_updater(msg[1], msg[2])
                elif msg[0] == "update_error":
                    if self._update_page:
                        self._update_page.show_error(msg[1])
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

    # ---- janelas ----------------------------------------------------------------------------
    def _show_stats(self) -> None:
        self._show_main("stats")

    def _show_main(self, page: str) -> None:
        if self._main_window and self._main_window.alive:
            self._main_window.show(page)
            return
        self._update_page = UpdatePage(lambda: self.app.updates.available, __version__, on_confirm=self._download,
                                       on_later=lambda: self._main_window and self._main_window.show("dashboard"))
        pages = [DashboardPage(self.app),
                 StatsPage(self.app.stats, lambda: self.app.config["daily_goal_minutes"]),
                 SettingsPage(self.app.config, self.app.stats, self.app.library, lambda: self.app.last_state),
                 self._update_page]
        available = lambda: self.app.updates.available.version if self.app.updates.available else None
        # O idioma vem direto do config: mudar nos Ajustes troca a janela na hora, sem esperar o loop.
        self._main_window = MainWindow(self.root, pages, lambda: Translator(self.app.config["language"]), available,
                                       page=page)

    def _show_welcome(self) -> None:
        """A primeira abertura, uma vez: depois de "Começar" (ou de fechar) não aparece mais."""
        if self.app.config["welcome_done"] or (self._welcome and self._welcome.alive):
            return

        def done():
            self.app.config.update("welcome_done", True)
            if self._welcome and self._welcome.alive:
                self._welcome.on_close = None
                self._welcome.close()

        page = WelcomePage(self.app.config, self.app.stats, on_start=done)
        self._welcome = MainWindow(self.root, [page], lambda: Translator(self.app.config["language"]), lambda: None,
                                   size=WELCOME_SIZE, min_size=WELCOME_SIZE, rail=False, on_close=done)
        self._welcome.win.resizable(False, False)

    # ---- atualização com um clique ---------------------------------------------------------
    def _show_update(self) -> None:
        if self.app.updates.available is not None:
            self._show_main("update")

    def _download(self, release: updates.Release) -> None:
        def run():
            try:
                path = updates.download(release, progress=lambda done, total: self._queue.put(("update_progress", done, total)))
            except updates.UpdateError as exc:
                log.warning("Atualização não baixada: %s", exc)
                self._queue.put(("update_error", str(exc)))
                return
            self._queue.put(("update_ready", path, release))
        threading.Thread(target=run, name="download", daemon=True).start()

    def _hand_over_to_updater(self, path: Path, release: updates.Release) -> None:
        """O atualizador espera este processo fechar; daqui em diante é com ele."""
        if self._update_page:
            self._update_page.set_ready()
        try:
            updates.start_updater(path, release)
        except OSError as exc:
            log.exception("Não consegui iniciar o atualizador")
            if self._update_page:
                self._update_page.show_error(str(exc))
            return
        self.root.after(1200, lambda: self._queue.put(("quit",)))   # dá tempo de ver "Conferido"

    def _announce_last_update(self) -> None:
        result = updates.pop_last_result()
        if not result:
            return
        if result.get("ok"):
            title, body = self.t("update_done_title"), self.t("update_done_body", version=result.get("para"))
        else:
            title = self.t("update_rollback_title")
            body = self.t("update_rollback_body", version=result.get("de"), error=result.get("erro") or "?")
        self._notify(title, body)

    def run(self) -> None:
        self.icon.run_detached()
        self.root.after(250, self._drain)
        self.root.after(1000, self._announce_last_update)
        self.root.after(1500, self._show_welcome)
        try:
            self.root.mainloop()
        finally:
            try:
                self.icon.stop()
            except Exception:
                pass
