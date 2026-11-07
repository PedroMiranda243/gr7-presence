import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from gr7_presence.i18n import Translator
from gr7_presence.stats import Stats
from gr7_presence.stats_page import StatsPage, level, nice_ticks

TODAY = date(2026, 11, 7)


def make_stats(test: unittest.TestCase, days_back: int = 20, preset: str = "Clean Cristalino") -> Stats:
    tmp = tempfile.TemporaryDirectory()
    stats = Stats(Path(tmp.name) / "stats.json")
    test.addCleanup(tmp.cleanup)
    for back in range(days_back):
        d = TODAY - timedelta(days=back)
        start = datetime(d.year, d.month, d.day, 20).timestamp()
        secs = 900.0 + 60 * (back % 5)
        stats.sessions.append({"start": start, "seconds": secs, "mode": "standalone", "host": None,
                               "days": {d.isoformat(): secs}, "presets": {preset: secs}, "amps": {"Plex": secs},
                               "last_preset": preset})
    return stats


class HelpersTest(unittest.TestCase):
    def test_ticks_like_the_mockup(self):
        ticks, top = nice_ticks(90)
        self.assertEqual(ticks, [0, 30, 60, 90])
        self.assertAlmostEqual(top, 99)
        ticks, _ = nice_ticks(360)
        self.assertEqual(ticks[1], 120)   # semanas: de 2 em 2 horas

    def test_calendar_levels(self):
        self.assertEqual([level(m * 60) for m in (0, 10, 20, 21, 45, 75, 76)], [0, 1, 1, 2, 2, 3, 4])


class StatsPageTest(unittest.TestCase):
    def render(self, stats: Stats, scale: float = 1.0, width: float = 882, lang: str = "pt", goal: int = 60):
        page = StatsPage(stats, lambda: goal, today=lambda: TODAY)
        return page, page.render(width, scale, Translator(lang))

    def test_renders_at_every_scale(self):
        stats = make_stats(self)
        for scale in (1.0, 1.25, 1.5, 2.0):
            _page, r = self.render(stats, scale)
            self.assertEqual(r.image.size, (round(882 * scale), round(r.height * scale)))

    def test_empty_and_english(self):
        _page, r = self.render(make_stats(self, 0))
        self.assertGreater(r.height, 600)
        _page, r = self.render(make_stats(self), lang="en", goal=0)
        self.assertGreater(r.height, 600)

    def test_goal_written_wrong_means_no_goal(self):
        page = StatsPage(make_stats(self), lambda: "meia hora", today=lambda: TODAY)
        self.assertEqual(page._collect()["goal"], 0)
        self.assertGreater(page.render(882, 1.0, Translator("pt")).height, 600)

    def test_long_names_and_narrow_window(self):
        stats = make_stats(self, preset="ABCD - Post Punk Lead 6 (Remastered Version With A Very Long Name)")
        _page, r = self.render(stats, width=782)
        self.assertEqual(r.image.width, 782)

    def test_period_buttons(self):
        page, r = self.render(make_stats(self))
        changed = []
        page.on_change = lambda: changed.append(page.period)
        self.assertEqual([reg.key for reg in r.regions], ["days", "weeks", "all"])
        r.regions[1].action()
        self.assertEqual((page.period, changed), ("weeks", ["weeks"]))
        r.regions[1].action()                      # de novo no mesmo: não redesenha à toa
        self.assertEqual(changed, ["weeks"])
        for period in ("weeks", "all"):
            page.period = period
            self.assertGreater(page.render(882, 1.0, Translator("pt")).height, 600)

    def test_live_session_shows_now(self):
        stats = make_stats(self, 3)
        start = datetime(2026, 11, 7, 21).timestamp()
        stats.start(start, "plugin", "REAPER")
        page = StatsPage(stats, lambda: 30, today=lambda: TODAY)
        facts = page._facts(page._collect(), Translator("pt"))
        self.assertEqual(facts[0][0], "3 dias seguidos")
        self.assertEqual(facts[0][1], "tocando. É o seu recorde!")


if __name__ == "__main__":
    unittest.main()
