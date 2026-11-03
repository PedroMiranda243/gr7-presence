import json
import tempfile
import unittest
from pathlib import Path

from gr7_presence.migrate import migrate


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class MigrateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.real = base / "Roaming" / "GR7 Presence"                       # AppData de verdade
        self.private = base / "Packages" / "Claude" / "GR7 Presence"        # cópia do app empacotado
        self.new = base / "projeto" / "dados"

    def tearDown(self):
        self.tmp.cleanup()

    def test_merges_both_copies(self):
        write(self.real / "config.json", {"client_id": "", "language": "pt"})
        write(self.private / "config.json", {"client_id": "123", "language": "pt", "rotate_seconds": 30})
        write(self.real / "stats.json", {"sessions": [{"start": 300.0, "mode": "standalone", "seconds": 400}]})
        write(self.private / "stats.json", {"sessions": [
            {"start": 100.0, "mode": "standalone", "seconds": 1479},
            {"start": 300.0, "mode": "standalone", "seconds": 120},   # mesma sessão, versão menor
        ]})
        write(self.private / "live_state.json", {"preset": "Chorus Bass"})

        self.assertTrue(migrate(self.new, [self.real, self.private]))
        cfg = json.loads((self.new / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["client_id"], "123")          # a config que tem o ID
        self.assertEqual(cfg["rotate_seconds"], 30)
        sessions = json.loads((self.new / "stats.json").read_text(encoding="utf-8"))["sessions"]
        self.assertEqual([(s["start"], s["seconds"]) for s in sessions], [(100.0, 1479), (300.0, 400)])
        self.assertTrue((self.new / "live_state.json").exists())

    def test_runs_only_once(self):
        write(self.private / "config.json", {"client_id": "123"})
        self.assertTrue(migrate(self.new, [self.private]))
        write(self.private / "config.json", {"client_id": "999"})
        self.assertFalse(migrate(self.new, [self.private]))
        self.assertEqual(json.loads((self.new / "config.json").read_text(encoding="utf-8"))["client_id"], "123")

    def test_nothing_to_migrate(self):
        self.assertFalse(migrate(self.new, []))
        self.assertFalse((self.new / "config.json").exists())


if __name__ == "__main__":
    unittest.main()
