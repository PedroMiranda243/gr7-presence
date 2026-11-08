import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

from gr7_presence import ui_kit as K
from gr7_presence import achievements as A
from gr7_presence.achievements import AchievementTracker
from gr7_presence.config import DEFAULTS
from gr7_presence.dashboard_page import NOTE, BottomPanel, DashboardPage
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


class AchievementPanelTest(unittest.TestCase):
    """O painel "Conquista nova" entra primeiro enquanto houver conquista não vista na página Conquistas."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.stats = Stats(Path(tmp.name) / "stats.json")
        self.app = FakeApp(self.stats)
        self.app.achievements = AchievementTracker(Path(tmp.name) / "conquistas.json", self.stats, lambda: 60)
        self.app.achievements.check(TODAY)                       # a primeira vez, em silêncio
        self.page = DashboardPage(self.app, today=lambda: TODAY, now=lambda: NOW)
        self.t = Translator("pt")

    def unlock_marathon(self):
        start = datetime(2026, 11, 7, 14).timestamp()
        self.stats.sessions.append({"start": start, "end": start + 7800, "seconds": 7800, "mode": "standalone",
                                    "days": {TODAY.isoformat(): 7800}, "presets": {"Clean Cristalino": 7800}})
        return self.app.achievements.check(TODAY)

    def test_only_with_something_new(self):
        titles = [panel.title for panel in self.page._panels(self.t, self.app.last_state)]
        self.assertNotIn("Conquista nova", titles)
        self.assertTrue(self.unlock_marathon())
        panels = self.page._panels(self.t, self.app.last_state)
        self.assertEqual([panel.title for panel in panels], ["Conquista nova", "Meta de hoje", "Conexões"])
        self.app.achievements.mark_seen()                        # abriu a página Conquistas
        self.assertNotIn("Conquista nova", [panel.title for panel in self.page._panels(self.t, None)])

    def test_button_opens_the_page(self):
        self.unlock_marathon()
        host = mock.Mock()
        self.page.host = host
        r = self.page.render(882, 1.0, self.t)
        button = next(reg for reg in r.regions if reg.key == "see_achievements")
        button.action()
        host.show.assert_called_once_with("achievements")
        for scale in (1.0, 1.25, 1.5, 2.0):
            self.assertEqual(self.page.render(882, scale, self.t).image.width, round(882 * scale))
        self.page.view_height = 1001                              # tela cheia: os três painéis lado a lado
        wide = self.page.render(1842, 1.0, self.t)
        self.assertEqual(self.page._layout(1842, 1.0, self.t, self.app.last_state)["cols"], 3)
        self.assertLessEqual(wide.height, 1001)
        self.assertTrue(any(reg.key == "see_achievements" for reg in wide.regions))

    def test_texts(self):
        self.unlock_marathon()
        self.unlock_marathon()                                     # 4 h 20 no dia: Dia puxado Ouro e mais
        with mock.patch.object(K.Painter, "text", autospec=True, side_effect=K.Painter.text) as text:
            self.page.render(882, 1.0, self.t)
        shown = [call.args[3] for call in text.call_args_list]
        self.assertIn("Dia puxado · Ouro", shown)                   # a que vale mais pontos
        more = next(s for s in shown if s.startswith("+40 pontos"))
        news = {u.key for u in A.unlocks(self.app.achievements.current(TODAY)) if u.mark in self.app.achievements.unseen()}
        self.assertTrue(more.endswith(f"e mais {len(news) - 1}"))      # conta conquistas, não níveis
        panel = self.page._panels(self.t, self.app.last_state)[0]
        m = K.Painter(1, 1, 1.0)
        self.assertGreaterEqual(panel.height(m, 320), 52 + 14 + 34)
        p = K.Painter(400, 200, 1.0)
        regions = panel.draw(p, 21, 10, 358)
        self.assertEqual(len(regions), 1)


class FullScreenTest(unittest.TestCase):
    """Tela cheia (opção B): o desenho da janela padrão ampliado por igual até ocupar a tela. Na janela
    padrão e nas menores, o desenho de sempre."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.app = FakeApp(Stats(Path(tmp.name) / "stats.json"))
        self.page = DashboardPage(self.app, today=lambda: TODAY, now=lambda: NOW)
        self.t = Translator("pt")

    def render(self, width: float, view_height: float, scale: float = 1.0):
        self.page.view_height = view_height
        return self.page.render(width, scale, self.t)

    def test_default_window_is_untouched(self):
        for width, height in ((882, 640), (782, 560), (882, 1000)):   # padrão, mínima, só mais alta
            plain = DashboardPage(self.app, today=lambda: TODAY, now=lambda: NOW).render(width, 1.0, self.t)
            r = self.render(width, height)
            self.assertEqual(self.page._place, (1.0, 0.0))
            self.assertEqual(r.image.tobytes(), plain.image.tobytes())

    def test_full_screen_fills_the_screen(self):
        for width, height, scale in ((1842, 1001, 1.0), (1842, 1001, 1.5), (2482, 1001, 1.0)):
            r = self.render(width, height, scale)
            zoom, dx = self.page._place
            self.assertGreater(zoom, 1.5)
            self.assertLessEqual(r.height, height)                     # cabe sem rolar
            self.assertTrue(r.height > 0.98 * height or dx < 10)        # ocupa a altura ou a largura
            self.assertAlmostEqual(dx * 2 + 882 * zoom, width)          # no meio da largura
            self.assertEqual(r.image.size, (round(width * scale), round(r.height * scale)))
            # O desenho da janela padrão na escala ampliada (o texto mede um tico diferente em cada escala).
            default = DashboardPage(self.app, today=lambda: TODAY, now=lambda: NOW).render(882, scale * zoom, self.t)
            self.assertEqual(len(default.regions), len(r.regions))
            for a, b in zip(default.regions, r.regions):                # os cliques acompanham o desenho
                self.assertEqual(a.key, b.key)
                self.assertAlmostEqual(b.x0, dx + a.x0 * zoom, places=3)
                self.assertAlmostEqual(b.y1, a.y1 * zoom, places=3)

    def test_wide_but_short_window_stays_inside(self):
        r = self.render(1800, 640)                                      # só mais larga que a padrão
        zoom, dx = self.page._place
        self.assertGreater(zoom, 1.0)                                   # cresce até a altura…
        self.assertLessEqual(r.height, 640)                             # …sem passar dela
        self.assertGreater(dx, 200)                                     # e o que sobra fica dos lados

    def with_extra_panels(self, n: int) -> None:
        """O Painel com `n` painéis a mais embaixo, como se ganhasse componentes novos."""
        usual = self.page._panels
        extra = [BottomPanel(f"Extra {i}", lambda m, w: 100, lambda p, x, y, w: p.text(x, y, "texto", NOTE))
                 for i in range(n)]
        self.page._panels = lambda t, state: usual(t, state) + extra

    def test_more_panels_scroll_in_the_default_window(self):
        self.with_extra_panels(4)
        r = self.render(882, 640)
        self.assertEqual(self.page._place, (1.0, 0.0))                  # nada de ampliar ou reorganizar
        self.assertEqual(self.page._layout(882, 1.0, self.t, self.app.last_state)["cols"], 2)
        self.assertGreater(r.height, 640)                               # a página rola, como as outras

    def test_more_panels_fit_the_full_screen(self):
        self.with_extra_panels(4)
        only_default_width = min(1842 / 882, 1001 / self.page._layout(882, 1.0, self.t, self.app.last_state)["total"])
        r = self.render(1842, 1001)
        zoom, dx = self.page._place
        layout_w = (1842 - 2 * dx) / zoom
        self.assertLessEqual(r.height, 1001)                            # tudo numa tela só
        self.assertGreater(zoom, only_default_width)                    # maior do que só ampliando
        self.assertGreaterEqual(self.page._layout(layout_w, zoom, self.t, self.app.last_state)["cols"], 3)

    def test_letters_never_shrink(self):
        self.with_extra_panels(20)                                      # nem em quatro colunas cabe
        r = self.render(1842, 1001)
        self.assertEqual(self.page._place, (1.0, 0.0))                  # o tamanho de letra da janela padrão
        self.assertEqual(self.page._layout(1842, 1.0, self.t, self.app.last_state)["cols"], 4)
        self.assertGreater(r.height, 1001)                              # e a página rola

    def test_pause_menu_grows_with_the_page(self):
        host = mock.Mock()
        self.page.host = host
        self.render(882, 0)
        normal = next(r for r in self.page.render(882, 1.0, self.t).regions if r.key == "pause")
        normal.action()
        x, y = host.open_menu.call_args.args[:2]
        r = self.render(1842, 1001)
        zoom, dx = self.page._place
        next(reg for reg in r.regions if reg.key == "pause").action()
        args, kwargs = host.open_menu.call_args
        self.assertAlmostEqual(args[0], dx + x * zoom)
        self.assertAlmostEqual(args[1], y * zoom)
        self.assertEqual(args[2], 220)                                  # a largura da lista normal…
        self.assertEqual(kwargs["zoom"], zoom)                          # …desenhada na escala ampliada


if __name__ == "__main__":
    unittest.main()
