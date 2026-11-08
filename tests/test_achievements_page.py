import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

from gr7_presence import achievements as A
from gr7_presence.achievement_view import medal_colors
from gr7_presence.achievements_page import AchievementsPage, badge, columns, highlights, pack
from gr7_presence.i18n import STRINGS, Translator
from gr7_presence.stats import Stats
from gr7_presence import ui_kit as K
from tests.test_achievements import JAN, daily, session

TODAY = date(2026, 11, 8)
# A página tem a largura da janela menos a barra lateral (78): janela mínima, a do exemplo, ~1120 e tela cheia.
WIDTHS = (782, 882, 1042, 1842)


def history(kind: str) -> list[dict]:
    """Sessões inventadas: nenhuma, poucas semanas ou meses de prática com DAW, presets e amplificadores."""
    if kind == "empty":
        return []
    days = 20 if kind == "half" else 240
    out = []
    for i in range(days):
        d = TODAY - timedelta(days=days - 1 - i)
        if i % 3 == 2 and kind == "full":
            continue
        out.append(session(datetime(d.year, d.month, d.day, 20), 45 + (i % 4) * 20,
                           presets={f"Timbre {i % 40:02d}": 1800}, amps={f"Amp {i % 9}": 1800}))
        if i % 10 == 0:
            out.append(session(datetime(d.year, d.month, d.day, 10), 40, mode="plugin", host="REAPER"))
    return out


def tracker(test: unittest.TestCase, kind: str = "full", goal: int = 30) -> A.AchievementTracker:
    tmp = tempfile.TemporaryDirectory()
    test.addCleanup(tmp.cleanup)
    stats = Stats(Path(tmp.name) / "stats.json")
    stats.sessions.extend(history(kind))
    return A.AchievementTracker(Path(tmp.name) / "conquistas.json", stats, lambda: goal)


def by_key(results: list[A.Result]) -> dict[str, A.Result]:
    return {r.key: r for r in results}


class TextsTest(unittest.TestCase):
    def test_every_achievement_has_texts_in_both_languages(self):
        for lang in ("pt", "en"):
            texts = STRINGS[lang]
            for d in A.CATALOG:
                self.assertIn(f"ach_{d.key}", texts, (lang, d.key))
                self.assertIn(f"ach_{d.key}_unit" if d.levels else f"ach_{d.key}_desc", texts, (lang, d.key))
            for group in A.GROUPS:
                self.assertIn(f"ach_group_{group}", texts, (lang, group))
            for level in range(1, 6):
                self.assertIn(f"ach_level_{level}", texts)

    def test_rail_label_fits(self):
        m = K.Painter(1, 1, 1.0)
        for lang in ("pt", "en"):
            self.assertLessEqual(m.measure(Translator(lang)("nav_achievements"), K.Style(10.5, 600, K.TEXT)), 60)


class BadgeTest(unittest.TestCase):
    t = Translator("pt")

    def results(self, sessions, goal=0):
        return by_key(A.evaluate(A.collect_facts(sessions, TODAY, goal)))

    def test_family_texts_and_bar(self):
        r = self.results(daily(JAN, 12))
        b = badge(r["hours"], self.t, TODAY)
        self.assertEqual((b.title, b.sub), ("Horas de prática", "Bronze · 12 de 50 h"))
        self.assertEqual((b.pips, b.level, b.colors), (5, 1, K.MEDAL_BRONZE))
        self.assertAlmostEqual(b.progress, 12 / 50)
        b = badge(r["full_months"], self.t, TODAY)
        self.assertEqual(b.sub, "0 de 1 mês")                       # singular quando a meta é 1
        self.assertIsNone(b.colors)
        b = badge(r["marathon"], self.t, TODAY)
        self.assertEqual(b.sub, "Bronze · 1 de 2 h")

    def test_decimals_go_down(self):
        r = self.results([session(datetime(2026, 3, 2, 14), 119)])  # 1 h 59: ainda não são 2 h
        self.assertEqual(badge(r["marathon"], self.t, TODAY).sub, "Bronze · 1,9 de 2 h")
        self.assertEqual(badge(r["marathon"], Translator("en"), TODAY).sub, "Bronze · 1.9 of 2 h")

    def test_maxed_new_data_singles_and_secrets(self):
        r = self.results(daily(JAN, 1, minutes=400, hour=8))         # uma sessão de 6 h 40
        b = badge(r["marathon"], self.t, TODAY)
        self.assertEqual((b.sub, b.progress, b.colors), ("Diamante · em 01/01", None, K.MEDAL_DIAMOND))
        self.assertEqual(badge(r["genres"], self.t, TODAY).sub, "Conta a partir da 1.5.0")
        self.assertEqual(badge(r["first"], self.t, TODAY).sub, "em 01/01")
        self.assertEqual(badge(r["first"], self.t, TODAY).colors, K.MEDAL_SINGLE)
        self.assertEqual(badge(r["bass"], self.t, TODAY).sub, "1 h com presets de baixo · desde a 1.5.0")
        locked = badge(r["insomnia"], self.t, TODAY)
        self.assertEqual((locked.icon, locked.title, locked.colors), ("question", "Secreta", None))
        self.assertEqual(medal_colors("insomnia", 1), K.MEDAL_SECRET)

    def test_one_year_counts_down(self):
        r = self.results(daily(date(2026, 3, 9), 1))
        first = r["first"].got
        self.assertEqual(badge(r["one_year"], self.t, TODAY, first).sub, "Faltam 121 dias")
        self.assertEqual(badge(r["one_year"], self.t, date(2027, 3, 8), first).sub, "Falta 1 dia")

    def test_highlights_recent_then_closest(self):
        results = A.evaluate(A.collect_facts(daily(JAN, 12), TODAY, 0))
        picks = highlights(results)
        self.assertEqual(len(picks), 5)
        newest = [u.key for u in A.unlocks(results)]
        self.assertEqual([r.key for r in picks[:3]], list(dict.fromkeys(newest))[:3])
        rest = picks[3:]
        self.assertTrue(all(r.definition.levels and not r.maxed for r in rest))
        self.assertGreaterEqual(rest[0].progress, rest[1].progress)
        empty = highlights(A.evaluate(A.collect_facts([], TODAY, 0)))
        self.assertEqual(len(empty), 5)                               # sem histórico: as primeiras do catálogo
        self.assertFalse(any(r.definition.secret or r.definition.new_data for r in empty))


class LayoutTest(unittest.TestCase):
    def test_columns(self):
        self.assertEqual([columns(w - 48) for w in WIDTHS], [5, 5, 5, 10])

    def test_pack_keeps_groups_whole(self):
        groups = [("a", [1] * 5), ("b", [1] * 3), ("c", [1] * 2), ("d", [1] * 4), ("e", [1] * 5)]
        rows = pack(groups, 5)
        self.assertEqual([[g[0] for g in row] for row, _used in rows], [["a"], ["b", "c"], ["d"], ["e"]])
        self.assertEqual([used for _row, used in pack(groups, 10)], [10, 9])


class PageTest(unittest.TestCase):
    def test_renders_everywhere(self):
        """Vazia, pela metade e cheia; nas quatro larguras e nas quatro escalas; em pt e en."""
        for kind in ("empty", "half", "full"):
            page = AchievementsPage(tracker(self, kind), today=lambda: TODAY)
            for width in WIDTHS:
                for scale in (1.0, 1.25, 1.5, 2.0):
                    r = page.render(width, scale, Translator("pt"))
                    self.assertEqual(r.image.size, (round(width * scale), round(r.height * scale)), (kind, width))
            self.assertGreater(page.render(882, 1.0, Translator("en")).height, 1000)

    def test_full_screen_fits_more(self):
        page = AchievementsPage(tracker(self), today=lambda: TODAY)
        normal = page.render(882, 1.0, Translator("pt")).height
        wide = page.render(1842, 1.0, Translator("pt")).height
        self.assertLess(wide, normal * 0.6)                           # dois grupos por linha e a linha do tempo ao lado

    def test_filters(self):
        page = AchievementsPage(tracker(self, "half"), today=lambda: TODAY)
        changed = []
        page.on_change = lambda: changed.append(page.filter)
        r = page.render(882, 1.0, Translator("pt"))
        self.assertEqual([reg.key for reg in r.regions], ["all", "got", "missing"])
        r.regions[1].action()
        self.assertEqual((page.filter, changed), ("got", ["got"]))
        results = page.tracker.current(TODAY)
        got = page._groups(results, Translator("pt"), TODAY)
        self.assertEqual(sum(len(items) for _t, items in got), sum(1 for r in results if r.level))
        page.filter = "missing"
        missing = page._groups(results, Translator("pt"), TODAY)
        self.assertEqual(sum(len(items) for _t, items in missing), sum(1 for r in results if not r.maxed))
        for width in (882, 1842):
            for f in ("got", "missing"):
                page.filter = f
                self.assertGreater(page.render(width, 1.0, Translator("pt")).height, 400)
        empty = AchievementsPage(tracker(self, "empty"), today=lambda: TODAY)
        empty.filter = "got"                                           # nada destravado: a página não quebra
        self.assertGreater(empty.render(882, 1.0, Translator("pt")).height, 300)

    def test_goal_achievements_only_with_a_goal(self):
        page = AchievementsPage(tracker(self, "half", goal=0), today=lambda: TODAY)
        groups = [title for title, _items in page._groups(page.tracker.current(TODAY), Translator("pt"), TODAY)]
        self.assertNotIn("Meta", groups)

    def test_opening_marks_as_seen(self):
        t = mock.Mock()
        AchievementsPage(t).on_show()
        t.mark_seen.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
