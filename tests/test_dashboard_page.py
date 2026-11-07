import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

from gr7_presence.config import DEFAULTS
from gr7_presence.dashboard_page import DashboardPage
from gr7_presence.detector import Target
from gr7_presence.gr7_state import PresetInfo
from gr7_presence.i18n import Translator
from gr7_presence.stats import Stats

TODAY = date(2026, 11, 7)
NOW = datetime(2026, 11, 7, 20, 56).timestamp()
PRESET = PresetInfo(name="Clean Cristalino", amp="Jump", chain=["Noise Gate", "Jump", "Studio Reverb"],
                    genres=["Rock"], characters=["Clean"], is_factory=False)


class Cfg(dict):
    def __getitem__(self, key):
        return self.get(key, DEFAULTS.get(key))


class FakeApp:
    def __init__(self, stats: Stats):
        self.config = Cfg(daily_goal_minutes=60)
        self.stats = stats
        self.paused = False
        self.pause_until = None
        self.discord_connected = True
        self.screen = "reading"
        self.last_state = (PRESET, Target("standalone", 1, NOW - 600), [], None)
        self.showing = {"activity": {"type": 0, "details": "🎸 Clean Cristalino", "state": "🔊 Jump",
                                     "timestamps": {"start": int((NOW - 600) * 1000)}},
                        "index": 1, "count": 3, "sent_at": NOW - 8, "rotate": 20}
        self.paused_calls = []

    def set_paused(self, paused, seconds=None):
        self.paused_calls.append((paused, seconds))
        self.paused = paused


class DashboardTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.stats = Stats(Path(tmp.name) / "stats.json")
        self.app = FakeApp(self.stats)
        self.page = DashboardPage(self.app, today=lambda: TODAY, now=lambda: NOW)
        self.t = Translator("pt")

    def played(self, day: date, minutes: float, preset="Clean Cristalino"):
        start = datetime(day.year, day.month, day.day, 20).timestamp()
        secs = minutes * 60
        self.stats.sessions.append({"start": start, "seconds": secs, "days": {day.isoformat(): secs},
                                    "presets": {preset: secs}, "last_preset": preset})

    def test_renders_every_state(self):
        for scale in (1.0, 1.5):
            self.assertEqual(self.page.render(882, scale, self.t).image.width, round(882 * scale))
        self.app.last_state = None
        self.app.screen = None
        self.assertGreater(self.page.render(882, 1.0, self.t).height, 300)   # Guitar Rig fechado
        self.app.last_state = (None, Target("plugin", 1, NOW - 60, host="REAPER"), [], None)
        self.assertGreater(self.page.render(882, 1.0, Translator("en")).height, 300)
        self.app.last_state = (PRESET, Target("standalone", 1, NOW), [], "empty")
        self.assertGreater(self.page.render(782, 1.0, self.t).height, 300)

    def test_titles(self):
        left = self.page._left(self.t, self.app.last_state)
        self.assertEqual(left["title"], "Clean Cristalino")
        self.assertEqual(left["meta"], "Preset próprio · Rock, Clean")
        self.assertEqual([amp for _label, amp in left["pills"]], [False, True, False])
        self.assertEqual(self.page._left(self.t, None)["title"], "Esperando o Guitar Rig 7")
        plugin = (None, Target("plugin", 1, NOW, host="REAPER"), [], None)
        self.assertEqual(self.page._left(self.t, plugin)["title"], "Guitar Rig 7 no REAPER")

    def test_last_session_when_closed(self):
        self.played(TODAY - timedelta(days=1), 58)
        self.assertEqual(self.page._last_session(self.t), "Última sessão: ontem, 20:00, 58 min com Clean Cristalino.")
        self.stats.sessions.clear()
        self.assertIsNone(self.page._last_session(self.t))

    def test_pause_menu_and_resume(self):
        host = mock.Mock()
        self.page.host = host
        pause = next(r for r in self.page.render(882, 1.0, self.t).regions if r.key == "pause")
        pause.action()
        options, pick = host.open_menu.call_args.args[3], host.open_menu.call_args.args[5]
        self.assertEqual([k for k, _ in options], ["hour", "forever"])
        pick("hour")
        self.assertEqual(self.app.paused_calls[-1], (True, 3600))
        resume = next(r for r in self.page.render(882, 1.0, self.t).regions if r.key == "resume")
        resume.action()
        self.assertEqual(self.app.paused_calls[-1], (False, None))

    def test_card_area(self):
        self.assertIsNone(self.page._empty_text(self.t, self.app.last_state))
        self.app.discord_connected = False
        self.assertIn("Discord está fechado", self.page._empty_text(self.t, self.app.last_state))
        self.app.paused = True
        self.assertIn("Pausado", self.page._empty_text(self.t, self.app.last_state))
        self.assertIn("Nada no seu perfil", self.page._empty_text(self.t, None))

    def test_goal_notes(self):
        self.assertEqual(self.page._goal_note(self.t, None), "Ainda dá tempo.")
        self.played(TODAY - timedelta(days=1), 90)
        self.assertEqual(self.page._goal_note(self.t, None), "Ainda dá tempo. Hoje seria o 2º dia seguido.")
        self.played(TODAY, 42)
        self.assertEqual(self.page._goal_note(self.t, None), "Faltam 18 min. Ontem você tocou 1 h 30.")
        self.played(TODAY, 30)
        self.assertEqual(self.page._goal_note(self.t, None), "Meta batida! Ontem você tocou 1 h 30.")
        self.app.config["daily_goal_minutes"] = 0
        self.assertEqual(self.page._goal_note(self.t, None), "Sem meta. Dá para definir uma nos Ajustes.")

    def test_connections(self):
        rows = self.page._connections(self.t, self.app.last_state)
        self.assertEqual([r[2] for r in rows], ["conectado", "aberto", "lendo"])
        self.app.screen = "minimized"
        self.app.discord_connected = False
        rows = self.page._connections(self.t, self.app.last_state)
        self.assertEqual([r[2] for r in rows], ["fechado", "aberto", "pausada"])
        self.assertIn("minimizada", rows[2][3])
        rows = self.page._connections(self.t, None)
        self.assertEqual([r[2] for r in rows], ["fechado", "fechado", "esperando"])


if __name__ == "__main__":
    unittest.main()
