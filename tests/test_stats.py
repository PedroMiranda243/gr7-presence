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

    def test_new_fields_for_achievements(self):
        """A partir da 1.5.0: tempo com preset próprio, por gênero, por fonte e com faixa no Tape Deck."""
        s = Stats(self.path)
        start = ts(date.today())
        s.start(start, "standalone")
        s._tick_at = start
        s.tick("Meu Timbre", "Bass Pro", now=start + 20, own=True, genres=("Rock", "Metal"), source="Bass", backing=True)
        s.tick("Clean Cristalino", "Jump", now=start + 40, genres=("Funk & Soul",), source="Guitar")
        s.tick(None, None, now=start + 70, backing=True)          # rack vazio, com a faixa tocando
        s.end()
        saved = json.loads(self.path.read_text(encoding="utf-8"))["sessions"][0]
        self.assertEqual(saved["own"], {"Meu Timbre": 20})
        self.assertEqual(saved["genres"], {"Rock": 20, "Metal": 20, "Funk & Soul": 20})
        self.assertEqual(saved["sources"], {"Bass": 20, "Guitar": 20})
        self.assertEqual(saved["backing"], 50)
        self.assertNotIn("tracks", saved)                         # o nome da faixa nunca é gravado

    def test_old_ticks_add_no_new_fields(self):
        s = Stats(self.path)
        self.play(s, ts(date.today()), 600)
        saved = json.loads(self.path.read_text(encoding="utf-8"))["sessions"][0]
        self.assertFalse({"own", "genres", "sources", "backing"} & set(saved))

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

    def test_seconds_on_a_day(self):
        s = Stats(self.path)
        today = date.today()
        self.play(s, ts(today), 600)
        self.play(s, ts(today - timedelta(days=1)), 300)
        s.sessions.append({"start": ts(today), "seconds": 120})   # sessão antiga, sem o "days"
        self.assertAlmostEqual(s.seconds_on(today), 720)

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


class PageNumbersTest(unittest.TestCase):
    """Os números da página Estatísticas: barras, conquistas e listas por período."""

    TODAY = date(2026, 11, 7)   # um sábado

    def session(self, d: date, minutes: float, preset="P", amp="A") -> dict:
        secs = minutes * 60
        return {"start": ts(d, 20), "seconds": secs, "days": {d.isoformat(): secs},
                "presets": {preset: secs}, "amps": {amp: secs}}

    def test_week_starts_on_sunday(self):
        self.assertEqual(stats_mod.week_start(self.TODAY), date(2026, 11, 1))
        self.assertEqual(stats_mod.week_start(date(2026, 11, 1)), date(2026, 11, 1))

    def test_day_totals_join_sessions(self):
        d = self.TODAY
        days = stats_mod.day_totals([self.session(d, 10), self.session(d, 5), {"start": ts(d), "seconds": 60}])
        self.assertEqual(days, {d: 960})

    def test_period_bars(self):
        days = {self.TODAY: 600, self.TODAY - timedelta(days=13): 60, self.TODAY - timedelta(days=14): 999}
        bars = stats_mod.period_bars(days, self.TODAY, "days")
        self.assertEqual(len(bars), 14)
        self.assertEqual((bars[0].seconds, bars[-1].seconds), (60, 600))
        self.assertEqual([b.current for b in bars].count(True), 1)
        self.assertTrue(bars[-1].current)

        weeks = stats_mod.period_bars(days, self.TODAY, "weeks")
        self.assertEqual(len(weeks), 16)
        self.assertEqual(weeks[-1].start, date(2026, 11, 1))
        self.assertEqual(weeks[-1].seconds, 600)
        self.assertEqual(weeks[-2].seconds, 60)         # 25/10 abre a semana de 25/10
        self.assertEqual(weeks[-3].seconds, 999)        # 24/10 ainda é da semana de 18/10

        months = stats_mod.period_bars({date(2025, 12, 31): 5, date(2026, 11, 2): 7}, self.TODAY, "all")
        self.assertEqual(len(months), 12)
        self.assertEqual((months[0].start, months[0].seconds), (date(2025, 12, 1), 5))
        self.assertEqual((months[-1].start, months[-1].seconds, months[-1].current), (date(2026, 11, 1), 7, True))

    def test_top_in_period(self):
        old = self.session(self.TODAY - timedelta(days=20), 300, preset="Antigo")
        new = self.session(self.TODAY, 10, preset="Novo")
        since = stats_mod.period_start(self.TODAY, "days")
        self.assertEqual(stats_mod.top_in([old, new], "presets", since), [("Novo", 600)])
        self.assertEqual(stats_mod.top_in([old, new], "presets", None)[0][0], "Antigo")
        self.assertEqual(stats_mod.sessions_since([old, new], self.TODAY - timedelta(days=6)), 1)


if __name__ == "__main__":
    unittest.main()
