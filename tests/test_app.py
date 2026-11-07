import copy
import tempfile
import unittest
from pathlib import Path

from gr7_presence.app import PresenceApp
from gr7_presence.config import DEFAULTS
from gr7_presence.detector import Target
from gr7_presence.gr7_state import PresetReader
from gr7_presence.live import LiveReading
from gr7_presence.preset_library import PresetLibrary
from gr7_presence.stats import Stats


class FakeConfig(dict):
    def __getitem__(self, key):
        return self.get(key, DEFAULTS.get(key))


class LiveStateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.app = PresenceApp(FakeConfig(copy.deepcopy(DEFAULTS)), Stats(base / "stats.json"),
                               PresetReader(base / "nao-existe.tle"), PresetLibrary(base, extra_dirs=[]),
                               live_state_path=base / "live_state.json")
        self.target = Target("standalone", 20744, 1_792_985_871.2)

    def tearDown(self):
        self.tmp.cleanup()

    def test_recall_same_run(self):
        self.app._remember_live(self.target, "IVP Bass")
        self.assertEqual(self.app._recall_live(self.target), ("IVP Bass", False))
        self.app._remember_live(self.target, "RTM2 Power", cleared=True)
        self.assertEqual(self.app._recall_live(self.target), ("RTM2 Power", True))

    def test_ignore_other_run(self):
        self.app._remember_live(self.target, "IVP Bass")
        reopened = Target("standalone", 20744, self.target.started_at + 600)   # GR7 reaberto
        self.assertEqual(self.app._recall_live(reopened), (None, False))
        self.assertEqual(self.app._recall_live(Target("standalone", 1, self.target.started_at)), (None, False))

    def test_missing_file(self):
        self.assertEqual(self.app._recall_live(self.target), (None, False))


class FakeLive:
    def __init__(self, readings):
        self.readings = list(readings)

    def read(self, pid):
        return self.readings.pop(0)


class RackStateTest(unittest.TestCase):
    """Clear Rack mantém o nome do preset no topo; o programa precisa perceber pelo rack vazio."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.app = PresenceApp(FakeConfig(copy.deepcopy(DEFAULTS)), Stats(base / "stats.json"),
                               PresetReader(base / "nao-existe.tle"), PresetLibrary(base, extra_dirs=[]),
                               live_state_path=base / "live_state.json")
        self.target = Target("standalone", 999_999_999, 1_792_985_871.2)   # pid inexistente: sem Tape Deck

    def tearDown(self):
        self.tmp.cleanup()

    def states(self, readings):
        self.app.live = FakeLive(readings)
        out = []
        for _ in readings:
            preset, _tracks, rack_state = self.app._current_state(self.target)
            out.append((preset.name if preset else None, rack_state))
        return out

    def test_clear_build_and_load_another(self):
        self.assertEqual(self.states([
            LiveReading("RTM2 Power", False),   # preset normal
            LiveReading("RTM2 Power", True),    # Clear Rack (o nome continua)
            None,                               # minimizado: mantém o estado
            LiveReading("RTM2 Power", False),   # efeitos adicionados depois de limpar
            LiveReading("Auto Rhythm", False),  # outro preset carregado
        ]), [("RTM2 Power", None), ("RTM2 Power", "empty"), ("RTM2 Power", "empty"),
             ("RTM2 Power", "scratch"), ("Auto Rhythm", None)])

    def test_cleared_state_survives_restart(self):
        self.states([LiveReading("RTM2 Power", True)])
        self.assertEqual(self.app._recall_live(self.target), ("RTM2 Power", True))


class GoalNoteTest(unittest.TestCase):
    """O aviso de meta batida sai uma vez, na virada, e só com o programa aberto."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        cfg = FakeConfig(copy.deepcopy(DEFAULTS))
        cfg["daily_goal_minutes"] = 10
        self.stats = Stats(base / "stats.json")
        self.app = PresenceApp(cfg, self.stats, PresetReader(base / "nao-existe.tle"), PresetLibrary(base, extra_dirs=[]),
                               live_state_path=base / "live_state.json")
        self.notes = []
        self.app.on_note = lambda title, body: self.notes.append((title, body))
        self.today = __import__("datetime").date.today()

    def play(self, seconds):
        start = __import__("time").time()
        self.stats.start(start, "standalone")
        self.stats._tick_at = start
        self.stats.tick("P", "A", now=start + 1)
        self.stats.current["days"][self.today.isoformat()] = seconds

    def test_notifies_once_when_crossing(self):
        self.play(500)
        self.app._check_goal(self.today)       # primeira volta: só marca o ponto de partida
        self.play(590)
        self.app._check_goal(self.today)
        self.assertEqual(self.notes, [])
        self.play(601)
        self.app._check_goal(self.today)
        self.assertEqual(len(self.notes), 1)
        self.assertEqual(self.notes[0][0], "Meta de hoje batida")
        self.assertIn("10 min", self.notes[0][1])
        self.play(900)
        self.app._check_goal(self.today)
        self.assertEqual(len(self.notes), 1)   # uma vez por dia

    def test_opening_above_the_goal_does_not_notify(self):
        self.play(1200)
        self.app._check_goal(self.today)
        self.play(1300)
        self.app._check_goal(self.today)
        self.assertEqual(self.notes, [])

    def test_switch_off_and_no_goal(self):
        self.app.config["notify_goal"] = False
        self.play(500)
        self.app._check_goal(self.today)
        self.play(700)
        self.app._check_goal(self.today)
        self.app.config["notify_goal"] = True
        self.app.config["daily_goal_minutes"] = 0
        self.play(800)
        self.app._check_goal(self.today)
        self.assertEqual(self.notes, [])

if __name__ == "__main__":
    unittest.main()
