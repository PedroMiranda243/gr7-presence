import copy
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

from gr7_presence.app import PresenceApp
from gr7_presence.config import DEFAULTS
from gr7_presence.gr7_state import PresetReader
from gr7_presence.i18n import Translator
from gr7_presence.main_window import MainWindow, render_rail
from gr7_presence.preset_library import PresetLibrary
from gr7_presence.stats import Stats
from gr7_presence.stats_page import StatsPage
from gr7_presence.tray import TrayUI
from gr7_presence.updates import Release, UpdateChecker


class FakeConfig(dict):
    def __getitem__(self, key):
        return self.get(key, DEFAULTS.get(key))


class RailTest(unittest.TestCase):
    def test_update_entry_only_with_a_new_version(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        page = StatsPage(Stats(Path(tmp.name) / "s.json"), lambda: 30)
        t = Translator("pt")
        without = render_rail(640, 1.0, [page], "stats", None, None, t)
        self.assertEqual([r.key for r in without.regions], ["stats"])
        with_update = render_rail(640, 1.5, [page], "stats", "stats", "1.4.0", t)
        self.assertEqual([r.key for r in with_update.regions], ["stats", "update"])
        self.assertEqual(with_update.image.size, (round(78 * 1.5), 960))


class MainWindowTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.stats = Stats(Path(tmp.name) / "s.json")

    def test_opens_draws_and_closes(self):
        updates = []
        page = StatsPage(self.stats, lambda: 30)
        win = MainWindow(self.root, [page], lambda: Translator("pt"), lambda: "1.4.0", lambda: updates.append(1))
        self.root.update()
        win.render_page()
        win.render_rail()
        self.assertIsNotNone(win._page)
        self.assertEqual([r.key for r in win._page.regions], ["days", "weeks", "all"])
        page.set_period("all")                    # o clique redesenha a página
        self.assertEqual(win._page.regions[2].key, "all")
        win._rail_click(mock.Mock(x=40 * win.scale, y=(640 - 14 - 20) * win.scale))
        self.assertEqual(updates, [1])
        win.close()
        self.assertFalse(win.alive)
        win.render_page()                         # depois de fechada, não faz nada nem quebra


class TrayOpensMainWindowTest(unittest.TestCase):
    def test_stats_menu_opens_the_new_window_once(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        app = PresenceApp(FakeConfig(copy.deepcopy(DEFAULTS)), Stats(base / "s.json"), PresetReader(base / "x.tle"),
                          PresetLibrary(base, extra_dirs=[]), live_state_path=base / "l.json",
                          updates=UpdateChecker("1.3.1", fetch=lambda: None))
        ui = TrayUI(app)
        self.addCleanup(ui.root.destroy)
        ui._show_stats()
        first = ui._main_window
        self.assertTrue(first.alive)
        ui._show_stats()
        self.assertIs(ui._main_window, first)     # a mesma janela volta para a frente
        app.updates.available = Release("1.4.0", "https://exemplo")
        self.assertEqual(first.update_version(), "1.4.0")
        first.close()


class KeyboardTest(unittest.TestCase):
    """Tab anda pelos controles desenhados, Enter aciona, e o contorno âmbar mostra onde está o foco."""

    def test_tab_enter_and_ring(self):
        root = tk.Tk()
        root.withdraw()
        self.addCleanup(root.destroy)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        page = StatsPage(Stats(Path(tmp.name) / "s.json"), lambda: 30)
        win = MainWindow(root, [page], lambda: Translator("pt"), lambda: None)
        self.addCleanup(lambda: win.alive and win.close())
        root.update()
        win.render_page()
        win.render_rail()
        targets = win._targets()
        self.assertEqual(targets, [("rail", "stats"), ("page", "days"), ("page", "weeks"), ("page", "all")])
        win._tab(1)
        win._tab(1)
        win._tab(1)
        self.assertEqual(win._kb, ("page", "weeks"))
        self.assertTrue(win.view.find_withtag("kbring"))
        win._activate()
        self.assertEqual(page.period, "weeks")
        win._tab(-1)
        self.assertEqual(win._kb, ("page", "days"))
        win._view_press(mock.Mock(x=-100, y=-100))   # o mouse tira o contorno
        self.assertFalse(win.view.find_withtag("kbring"))


if __name__ == "__main__":
    unittest.main()
