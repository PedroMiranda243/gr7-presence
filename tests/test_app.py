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


if __name__ == "__main__":
    unittest.main()
