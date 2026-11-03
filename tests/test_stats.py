import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from gr7_presence import stats as stats_mod
from gr7_presence.stats import Stats, _streaks


def ts(d: date, hour: int = 12) -> float:
    return datetime(d.year, d.month, d.day, hour).timestamp()


class StatsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "stats.json"

    def tearDown(self):
        self.tmp.cleanup()

    def play(self, stats: Stats, start: float, seconds: int, preset="RTM2 Power", amp="Van 51"):
        stats.start(start, "standalone")
        stats._tick_at = start
        for i in range(1, seconds // 10 + 1):
            stats.tick(preset, amp, now=start + i * 10)
        stats.end()

    def test_session_is_saved_and_reloaded(self):
        s = Stats(self.path)
        self.play(s, ts(date.today()), 600)
        self.assertEqual(len(Stats(self.path).sessions), 1)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertAlmostEqual(data["sessions"][0]["seconds"], 600)
        self.assertAlmostEqual(data["sessions"][0]["presets"]["RTM2 Power"], 600)

    def test_short_session_is_dropped(self):
        s = Stats(self.path)
        self.play(s, ts(date.today()), 30)
        self.assertEqual(Stats(self.path).sessions, [])

    def test_ticks_are_capped(self):
        s = Stats(self.path)
        start = ts(date.today())
        s.start(start, "standalone")
        s._tick_at = start
        s.tick(None, None, now=start + 3 * 3600)   # PC suspenso por 3 horas
        self.assertEqual(s.current["seconds"], stats_mod.MAX_TICK_SECONDS)

    def test_summary(self):
        s = Stats(self.path)
        today = date.today()
        for back in range(3):
            self.play(s, ts(today - timedelta(days=back)), 600, preset=f"P{back}", amp="Plex" if back else "Van 51")
        self.play(s, ts(today - timedelta(days=30)), 1200, preset="P0")
        summary = s.summary(today=today)
        self.assertAlmostEqual(summary.today, 600)
        self.assertAlmostEqual(summary.week, 1800)
        self.assertAlmostEqual(summary.total, 3000)
        self.assertEqual(summary.sessions, 4)
        self.assertEqual(summary.streak, 3)
        self.assertEqual(summary.top_presets[0], ("P0", 1800))
        self.assertEqual(summary.top_amps[0][0], "Van 51")

    def test_current_session_counts_live(self):
        s = Stats(self.path)
        start = ts(date.today())
        s.start(start, "standalone")
        s._tick_at = start
        s.tick("X", None, now=start + 20)
        self.assertAlmostEqual(s.summary().today, 20)

    def test_corrupted_file_is_backed_up(self):
        self.path.write_text("{not json", encoding="utf-8")
        s = Stats(self.path)
        self.assertEqual(s.sessions, [])
        self.assertTrue(any(p.name.startswith("stats.corrompido") for p in self.path.parent.iterdir()))


class StreakTest(unittest.TestCase):
    def test_streak_rules(self):
        today = date(2026, 10, 26)
        day = lambda n: (today - timedelta(days=n)).isoformat()
        full = stats_mod.STREAK_DAY_SECONDS
        # hoje ainda não tocou: a sequência que terminou ontem continua valendo
        self.assertEqual(_streaks({day(1): full, day(2): full}, today), (2, 2))
        # buraco anteontem
        self.assertEqual(_streaks({day(0): full, day(1): full, day(3): full}, today), (2, 2))
        # dias com menos de 5 min não contam
        self.assertEqual(_streaks({day(0): full - 1}, today), (0, 0))
        # recorde antigo
        old = {day(n): full for n in range(10, 17)}
        self.assertEqual(_streaks({**old, day(0): full}, today), (1, 7))


if __name__ == "__main__":
    unittest.main()
