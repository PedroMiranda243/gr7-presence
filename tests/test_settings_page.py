import json
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

from gr7_presence.config import Config
from gr7_presence.detector import Target
from gr7_presence.gr7_state import PresetInfo
from gr7_presence.i18n import Translator
from gr7_presence.main_window import MainWindow
from gr7_presence.settings_page import SettingsPage, valid_url
from gr7_presence.stats import Stats

PRESET = PresetInfo(name="Clean Cristalino", amp="Jump", chain=["Noise Gate", "Jump", "Studio Reverb"],
                    genres=["Rock"], characters=["Clean"])


class FakeAutostart:
    def __init__(self):
        self.enabled = False

    def is_enabled(self):
        return self.enabled

    def set_enabled(self, value):
        self.enabled = value


class SettingsPageTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.config = Config(self.base / "config.json")
        self.stats = Stats(self.base / "stats.json")
        self.opened = []
        self.state = (PRESET, Target("standalone", 0, time.time() - 60), [], None)
        self.page = SettingsPage(self.config, self.stats, None, lambda: self.state, autostart=FakeAutostart(),
                                 open_path=self.opened.append)
        self.changes = []
        self.page.on_change = lambda: self.changes.append(1)

    def render(self, lang="pt", scale=1.0):
        return self.page.render(538, scale, Translator(lang))

    def region(self, key):
        return next(r for r in self.render().regions if r.key == key)

    def saved(self) -> dict:
        return json.loads(self.config.path.read_text(encoding="utf-8"))

    def test_renders_both_columns_at_every_scale(self):
        for scale in (1.0, 1.5, 2.0):
            r = self.render(scale=scale)
            self.assertEqual(r.image.width, round(538 * scale))
            side = self.page.render_side(344, 640, scale, Translator("pt"))
            self.assertEqual(side.image.size, (round(344 * scale), round(640 * scale)))
        self.assertEqual([f.key for f in self.render().fields], ["btn0_label", "btn0_url", "btn1_label", "btn1_url"])

    def test_switch_saves_and_reloads_the_loop(self):
        self.region("show_preset").action()
        self.assertFalse(self.saved()["show_preset"])
        self.assertTrue(self.config.reload_if_changed())   # o loop vê a mudança e reaplica
        self.assertTrue(self.changes)

    def test_preview_follows_the_options(self):
        t = Translator("pt")
        activities, _ = self.page.preview(t)
        self.assertEqual(activities[0]["details"], "🎸 Clean Cristalino")
        self.config.update("show_preset", False)
        self.config.update("show_tags", False)
        self.config.update("show_stats", False)
        activities, _ = self.page.preview(t)
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]["details"], "🎸 Tocando guitarra")

    def test_preview_with_guitar_rig_closed(self):
        self.state = None
        activities, target = self.page.preview(Translator("pt"))
        self.assertEqual(activities[0]["details"], "🎸 Meu preset")   # ninguém tocou ainda: um exemplo
        self.assertLess(target.started_at, time.time())

    def test_slider_snaps_to_5_seconds_and_saves_on_release(self):
        r = self.region("rotate_seconds")
        r.drag(r.x0 + 4 + 8 + (150 - 16) * 0.5, 0)            # metade: 37,5 → 40 s
        self.assertEqual(self.page._rotate_value(), 40)
        self.assertEqual(self.saved()["rotate_seconds"], 20)  # ainda não gravou
        self.page.end_drag()
        self.assertEqual(self.saved()["rotate_seconds"], 40)
        r.drag(r.x0 - 500, 0)
        self.page.end_drag()
        self.assertEqual(self.saved()["rotate_seconds"], 15)  # nunca abaixo do limite do Discord

    def test_slider_with_the_keyboard(self):
        r = self.region("rotate_seconds")
        r.step(1)
        self.assertEqual(self.saved()["rotate_seconds"], 25)
        for _ in range(20):
            self.region("rotate_seconds").step(-1)
        self.assertEqual(self.saved()["rotate_seconds"], 15)

    def test_buttons_are_saved_when_typing_stops(self):
        host = mock.Mock()
        self.page.host = host
        field = next(f for f in self.render().fields if f.key == "btn1_url")
        field.on_change("www.sem-https.com")
        self.assertEqual(host.later.call_args.kwargs["key"], "buttons")
        self.assertTrue(self.render().image)   # com o aviso de link errado
        host.later.call_args.args[1]()          # o tempo de espera passou
        self.assertEqual(self.saved()["buttons"][1]["url"], "www.sem-https.com")
        activities, _ = self.page.preview(Translator("pt"))
        self.assertEqual(len(activities[0].get("buttons", [])), 1)   # o botão com link errado não vai

    def test_valid_url(self):
        self.assertTrue(valid_url("https://youtube.com/@canal"))
        self.assertFalse(valid_url("www.youtube.com"))
        self.assertFalse(valid_url("https://"))

    def test_autostart_shows_at_once(self):
        r = next(r for r in self.render().regions if r.key == "Iniciar com o Windows")
        r.action()
        self.assertTrue(self.page._autostart_on())
        for _ in range(50):
            if self.page.autostart.enabled:
                break
            time.sleep(0.02)
        self.assertTrue(self.page.autostart.enabled)

    def test_advanced_buttons_open_files(self):
        self.region("Abrir config.json").action()
        self.assertEqual(self.opened, [self.config.path])

    def test_language_and_goal(self):
        self.region("en").action()
        self.assertEqual(self.saved()["language"], "en")
        self.config.data["daily_goal_minutes"] = 40     # valor fora da lista entra nas opções
        self.assertGreater(self.render(lang="en").height, 900)

    def test_select_opens_the_menu_and_picks(self):
        host = mock.Mock()
        self.page.host = host
        self.region("activity_type").action()
        args = host.open_menu.call_args.args
        self.assertEqual([v for v, _ in args[3]], ["playing", "listening", "watching", "competing"])
        args[5]("watching")
        self.assertEqual(self.saved()["activity_type"], "watching")


class SettingsWindowTest(unittest.TestCase):
    def test_fields_and_side_panel_in_the_window(self):
        root = tk.Tk()
        root.withdraw()
        self.addCleanup(root.destroy)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        page = SettingsPage(Config(base / "c.json"), Stats(base / "s.json"), None, lambda: None,
                            autostart=FakeAutostart(), open_path=lambda _p: None)
        win = MainWindow(root, [page], lambda: Translator("pt"), lambda: None, lambda: None)
        self.addCleanup(lambda: win.alive and win.close())
        root.update()
        win.render_page()
        win.render_side()
        self.assertEqual(set(win._entries), {"btn0_label", "btn0_url", "btn1_label", "btn1_url"})
        self.assertIsNotNone(win._side)
        entry = win._entries["btn1_label"]
        self.assertTrue(entry.showing_placeholder)      # o texto de exemplo, não um valor
        win.open_menu(100, 100, 200, [(1, "Um"), (2, "Dois")], 1, lambda _v: None)
        self.assertIsNotNone(win._menu)
        win.close_menu()
        self.assertIsNone(win._menu)


if __name__ == "__main__":
    unittest.main()
