"""Página Atualização, primeira abertura e o menu curto da bandeja."""
import copy
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

from gr7_presence.app import PresenceApp
from gr7_presence.config import DEFAULTS, Config
from gr7_presence.gr7_state import PresetReader
from gr7_presence.i18n import Translator
from gr7_presence.preset_library import PresetLibrary
from gr7_presence.stats import Stats
from gr7_presence.tray import TrayUI
from gr7_presence.update_page import UpdatePage
from gr7_presence.updates import Release, UpdateChecker
from gr7_presence.welcome_page import WelcomePage

NOTES = "### Como atualizar\n- Pela bandeja.\n\n### Mudanças\n- **Painel** novo\n  - com o cartão\n"
RELEASE = Release("1.4.0", "https://github.com/x/releases/tag/v1.4.0", "https://github.com/x.zip", "abc", NOTES,
                  size=2_000_000)


class UpdatePageTest(unittest.TestCase):
    def setUp(self):
        self.confirmed, self.later, self.opened = [], [], []
        self.release = RELEASE
        self.page = UpdatePage(lambda: self.release, "1.3.1", self.confirmed.append, lambda: self.later.append(1),
                               open_url=self.opened.append)
        self.page.on_change = lambda: None

    def keys(self, lang="pt"):
        return {r.key: r for r in self.page.render(882, 1.0, Translator(lang)).regions}

    def test_buttons(self):
        regions = self.keys()
        self.assertEqual(set(regions), {"update_now", "later", "github"})
        regions["github"].action()
        self.assertEqual(self.opened, [RELEASE.url])
        regions["later"].action()
        self.assertEqual(self.later, [1])
        regions["update_now"].action()
        regions["update_now"].action()           # o segundo clique, durante o download, não baixa de novo
        self.assertEqual(self.confirmed, [RELEASE])
        self.assertEqual(set(self.keys()), {"github"})   # enquanto baixa, só o link

    def test_progress_ready_and_error(self):
        self.page.set_progress(500_000, 2_000_000)
        self.assertGreater(self.page.render(882, 1.5, Translator("en")).height, 400)
        self.page.set_ready()
        self.assertEqual(self.page.state, "ready")
        self.page.show_error("sem internet")
        self.assertIn("update_now", self.keys())      # dá para tentar de novo

    def test_without_a_release(self):
        self.release = None
        self.assertEqual(set(self.keys()), {"later"})


class WelcomePageTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.config = Config(base / "config.json")
        self.started = []
        auto = mock.Mock()
        auto.state = False
        auto.is_enabled.side_effect = lambda: auto.state
        auto.set_enabled.side_effect = lambda value: setattr(auto, "state", value)
        self.page = WelcomePage(self.config, Stats(base / "s.json"), on_start=lambda: self.started.append(1),
                                autostart=auto, checks=lambda: (True, False, True))
        self.page.on_change = lambda: None

    def test_goal_start_and_autostart(self):
        regions = {r.key: r for r in self.page.render(720, 1.0, Translator("pt")).regions}
        self.assertEqual(set(regions), {"0", "20", "30", "60", "autostart", "start"})
        regions["60"].action()
        self.assertEqual(self.config["daily_goal_minutes"], 60)
        regions["autostart"].action()
        self.assertTrue(self.page._autostart_on())
        regions["start"].action()
        self.assertEqual(self.started, [1])

    def test_renders_in_both_languages_and_scales(self):
        for lang, scale in (("pt", 1.0), ("en", 1.5)):
            img = self.page.render(720, scale, Translator(lang)).image
            self.assertEqual(img.width, round(720 * scale))


class FakeConfig(dict):
    def __getitem__(self, key):
        return self.get(key, DEFAULTS.get(key))

    def update(self, key, value):
        self[key] = value


class TrayMenuTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.app = PresenceApp(FakeConfig(copy.deepcopy(DEFAULTS)), Stats(base / "s.json"), PresetReader(base / "x.tle"),
                               PresetLibrary(base, extra_dirs=[]), live_state_path=base / "l.json",
                               updates=UpdateChecker("1.3.1", fetch=lambda: None))
        self.ui = TrayUI(self.app)
        self.addCleanup(self.ui.root.destroy)
        self.ui.icon = mock.Mock(visible=True)

    def visible(self):
        out = []
        for item in self.ui._menu().items:
            if item is not None and item.visible and str(item.text) and str(item.text) != "- - - -":
                out.append(str(item.text))
        return out

    def test_short_menu(self):
        items = self.visible()
        self.assertEqual(items[1:], ["Abrir o GR7 Presence", "Pausar por 1 hora", "Pausar até eu voltar", "Sair"])
        self.app.set_paused(True, 3600)
        self.assertIn("Voltar a mostrar", self.visible())
        self.assertNotIn("Pausar por 1 hora", self.visible())
        self.app.updates.available = RELEASE
        self.assertIn("Atualizar para a versão 1.4.0", self.visible())

    def test_update_flow_goes_to_the_page(self):
        self.app.updates.available = RELEASE
        self.ui._queue.put(("open", "update"))
        self.ui._drain()
        win = self.ui._main_window
        self.addCleanup(lambda: win.alive and win.close())
        self.assertEqual(win.current, "update")
        self.ui._queue.put(("update_progress", 10, 100))
        self.ui._drain()
        self.assertEqual((self.ui._update_page.state, self.ui._update_page.done), ("downloading", 10))
        self.ui._queue.put(("update_error", "sem internet"))
        self.ui._drain()
        self.assertEqual(self.ui._update_page.error, "sem internet")

    def test_welcome_only_once(self):
        self.ui._show_welcome()
        first = self.ui._welcome
        self.assertTrue(first.alive)
        self.ui._show_welcome()
        self.assertIs(self.ui._welcome, first)
        first.close()                                  # fechar pelo X também conta
        self.assertTrue(self.app.config["welcome_done"])
        self.ui._show_welcome()
        self.assertIs(self.ui._welcome, first)         # não abre de novo


if __name__ == "__main__":
    unittest.main()
