import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

from PIL import ImageColor

from gr7_presence.i18n import Translator
from gr7_presence.stats import Stats
from gr7_presence import ui_kit as K
from gr7_presence.stats_page import (CAL_GAP, CAL_LEFT, CAL_WEEKS, CHART_W_BASE, StatsPage, calendar_grid, level,
                                     nice_ticks)

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

    def test_calendar_fills_the_panel(self):
        # Larguras internas do painel: janela mínima, a do exemplo (960), ~1120 e tela cheia em 1920.
        for width in (318, 368, 446, 838):
            weeks, step = calendar_grid(width)
            self.assertGreaterEqual(weeks, CAL_WEEKS)
            self.assertAlmostEqual(CAL_LEFT + weeks * step - CAL_GAP, width)   # a última coluna encosta na borda
            self.assertTrue(12 <= step - CAL_GAP <= 15, (width, step))          # quadradinho perto dos 13 do exemplo
        self.assertGreater(calendar_grid(446)[0], calendar_grid(368)[0])      # janela mais larga: mais semanas

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

    def track_widths(self, width: float) -> list[float]:
        """Largura dos trilhos das barras de presets e amplificadores, desenhados com o tom TRACK e 6 de altura."""
        widths = []
        original = K.Painter.rrect

        def spy(painter, x, y, w, h, r, fill, *args, **kwargs):
            if fill == K.TRACK and h == 6:
                widths.append(round(w, 1))
            return original(painter, x, y, w, h, r, fill, *args, **kwargs)

        with mock.patch.object(K.Painter, "rrect", spy):
            self.render(make_stats(self), width=width)
        return widths

    def test_list_bars_take_the_extra_width(self):
        self.assertEqual(set(self.track_widths(882)), {92})       # na janela do exemplo, como no exemplo
        wide = self.track_widths(1042)                            # janela de ~1120 px
        self.assertEqual(len(set(wide)), 1)
        self.assertAlmostEqual(wide[0], 92 + (1042 - 882) / 2, delta=0.1)   # o que a coluna cresceu vai para a barra

    def bar_widths(self, width: float, period: str = "days") -> set[float]:
        """As larguras das barras do gráfico (as com tempo; dia sem tempo é um traço)."""
        widths = []
        original = K.Painter.top_rounded_bar

        def spy(painter, x, y, w, h, *args, **kwargs):
            widths.append(round(w, 1))
            return original(painter, x, y, w, h, *args, **kwargs)

        page = StatsPage(make_stats(self), lambda: 30, today=lambda: TODAY)
        page.period = period
        with mock.patch.object(K.Painter, "top_rounded_bar", spy):
            page.render(width, 1.0, Translator("pt"))
        return set(widths)

    def test_bars_grow_in_full_screen(self):
        """Opção B, escolhida pelo dono do projeto: em tela cheia a barra engorda até 44 px; na janela
        padrão, continua a do exemplo."""
        self.assertEqual(self.bar_widths(882), {22})
        self.assertEqual(self.bar_widths(882, "weeks"), {19.5})         # 16 semanas: 62 % do espaço, como antes
        for period in ("days", "weeks", "all"):
            self.assertEqual(self.bar_widths(1842, period), {44})       # janela maximizada em 1920 px
        middle = self.bar_widths(1042).pop()                            # janela de ~1120 px: no meio do caminho
        self.assertTrue(22 < middle < 44, middle)

    def test_chart_width_in_the_default_window(self):
        """A barra só engorda num gráfico mais largo que o da janela padrão: confere que a constante bate."""
        seen = []
        original = StatsPage._bars

        def spy(page, p, x0, y0, w, *args, **kwargs):
            seen.append(w)
            return original(page, p, x0, y0, w, *args, **kwargs)

        with mock.patch.object(StatsPage, "_bars", spy):
            self.render(make_stats(self), width=882)
        self.assertEqual(seen, [CHART_W_BASE])

    def test_goal_line_in_front_of_the_bars(self):
        order = []
        hline, bar = K.Painter.hline, K.Painter.top_rounded_bar

        def spy_hline(painter, x1, x2, y, color, width=1, dash=None):
            if color == K.AMBER and dash:
                order.append("meta")
            return hline(painter, x1, x2, y, color, width, dash)

        def spy_bar(painter, *args, **kwargs):
            order.append("barra")
            return bar(painter, *args, **kwargs)

        with mock.patch.object(K.Painter, "hline", spy_hline), mock.patch.object(K.Painter, "top_rounded_bar", spy_bar):
            self.render(make_stats(self), goal=15)
        self.assertEqual(order[:15], ["barra"] * 14 + ["meta"])   # as 14 barras do gráfico, depois a meta

    def test_goal_outline_only_over_the_bars(self):
        """Sobre a barra, o traço ganha contorno escuro (a barra de hoje também é âmbar); fora dela, não."""
        p = K.Painter(200, 20, 1.0, K.BG)
        p.rect(90, 0, 22, 20, K.AMBER)                          # a barra de hoje, de x = 90 a 112
        StatsPage._goal_line(p, 0, 200, 10, [90], 22)
        color = lambda x, y: p.img.getpixel((x, y))[:3]         # noqa: E731
        self.assertEqual(color(92, 9), ImageColor.getrgb(K.AMBER))   # o traço
        self.assertEqual(color(92, 8), ImageColor.getrgb(K.STAGE))   # o contorno, na barra
        self.assertEqual(color(96, 8), ImageColor.getrgb(K.AMBER))   # entre dois traços, a barra aparece
        self.assertEqual(color(2, 9), ImageColor.getrgb(K.AMBER))    # o traço fora da barra
        self.assertEqual(color(2, 8), ImageColor.getrgb(K.BG))       # sem contorno fora da barra

    def test_total_with_hours_and_minutes(self):
        page = StatsPage(make_stats(self), lambda: 30, today=lambda: TODAY)
        facts = page._facts(page._collect(), Translator("pt"))
        self.assertEqual(facts[2][0], "5 h 40 min")   # 20 sessões, 20 400 s; antes aparecia só "5 h"

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
