import copy
import unittest
from datetime import date, datetime

from gr7_presence import achievements as A
from gr7_presence import achievement_view as V
from gr7_presence.config import DEFAULTS
from gr7_presence.detector import Target
from gr7_presence.i18n import STRINGS, Translator
from gr7_presence.presence import build_activity, build_cards
from gr7_presence.stats import Summary
from tests.test_achievements import JAN, daily, session

pt, en = Translator("pt"), Translator("en")


class FakeConfig(dict):
    def __getitem__(self, key):
        return self.get(key, DEFAULTS.get(key))


def results(sessions, goal=0) -> list[A.Result]:
    return A.evaluate(A.collect_facts(sessions, date(2026, 12, 31), goal))


def unlock(key: str, level: int = 1, got: date = JAN) -> A.Unlock:
    mark = f"{key}:{level}" if A.BY_KEY[key].levels else key
    return A.Unlock(mark, key, level, got, A.mark_points(key, level))


class TextsTest(unittest.TestCase):
    def test_every_family_says_what_it_counts(self):
        for lang in ("pt", "en"):
            for d in A.CATALOG:
                if d.levels:
                    self.assertIn(f"ach_{d.key}_what", STRINGS[lang], (lang, d.key))
            for key in V.UNIT_ONE:
                self.assertIn(f"ach_{key}_what_one", STRINGS[lang])
                self.assertIn(f"ach_{key}_unit_one", STRINGS[lang])

    def test_labels_and_numbers(self):
        self.assertEqual(V.mark_label(unlock("marathon", 3), pt), "Maratona (Ouro)")
        self.assertEqual(V.mark_title(unlock("marathon", 3), pt), "Maratona · Ouro")
        self.assertEqual(V.mark_label(unlock("owl"), en), "Night owl")
        self.assertEqual(V.thousands(1060, pt), "1.060")
        self.assertEqual(V.thousands(1060, en), "1,060")
        self.assertEqual(V.unit("full_months", 1, pt), "mês")
        self.assertEqual(V.unit("full_months", 3, pt), "meses")

    def test_what(self):
        r = {x.key: x for x in results([session(datetime(2026, 3, 2, 14), 204)])}   # 3 h 24 numa sessão
        self.assertEqual(V.what("marathon", r, pt), "Sua maior sessão: 3 h 24 min")
        self.assertEqual(V.what("long_day", r, pt), "Seu maior dia: 3 h 24 min")
        self.assertEqual(V.what("owl", r, pt), "Tocar entre 0 h e 5 h")
        r = {x.key: x for x in results(daily(date(2026, 2, 1), 20, minutes=10))}
        self.assertEqual(V.what("full_months", r, pt), "1 mês com 20 dias tocados")
        self.assertEqual(V.what("streak", r, en), "20 days in a row")


class NoteTest(unittest.TestCase):
    def test_one(self):
        r = results([session(datetime(2026, 3, 2, 14), 204)])
        title, body = V.note([unlock("marathon", 3)], r, pt)
        self.assertEqual(title, "Conquista nova: Maratona (Ouro)")
        level = A.musician_level(A.total_points(r))[0]
        self.assertEqual(body, f"Sua maior sessão: 3 h 24 min. +40 pontos, nível {level}.")

    def test_many_in_one_notice(self):
        r = results([session(datetime(2026, 3, 2, 14), 204)])
        title, body = V.note([unlock("marathon", 1), unlock("marathon", 2), unlock("marathon", 3),
                              unlock("long_day", 2), unlock("first")], r, pt)
        self.assertEqual(title, "3 conquistas novas")                    # a Maratona entra uma vez, a mais alta
        self.assertIn("Maratona (Ouro)", body)
        self.assertNotIn("Prata", body.replace("Dia puxado (Prata)", ""))
        self.assertTrue(body.endswith("Veja na página Conquistas."))
        many = [unlock(k) for k in ("first", "owl", "early", "comeback", "two_worlds")]
        _title, body = V.note(many, r, pt)
        self.assertIn(" e mais 2.", body)
        _title, body = V.note(many[:2], r, en)
        self.assertIn(" and ", body)

    def test_nothing_new(self):
        self.assertIsNone(V.note([], [], pt))

    def test_first_time(self):
        r = results(daily(JAN, 12))
        title, body = V.first_note(14, r, pt)
        self.assertEqual(title, "As conquistas chegaram")
        self.assertIn("Você já tem 14 marcas", body)


class DiscordCardTest(unittest.TestCase):
    def setUp(self):
        self.cfg = FakeConfig(copy.deepcopy(DEFAULTS))
        self.target = Target("standalone", 1, 1_700_000_000.0)
        self.summary = Summary(today=600, week=600, total=40000, sessions=12, streak=3, best_streak=3,
                               top_presets=[], top_amps=[], recent=[])
        self.results = results([session(datetime(2026, 3, 2, 14), 204)])

    def cards(self, card):
        achievement, level = V.card_bits(card, self.results, pt)
        return build_cards(None, self.target, self.summary, self.cfg, pt, [], None, achievement, level)

    def test_card_for_24_hours(self):
        cards = self.cards(unlock("marathon", 3))
        self.assertEqual([c.key for c in cards][-1], "achievement")
        card = cards[-1]
        self.assertEqual(card.state, "🏆 Conquista: Maratona (Ouro)")
        self.assertEqual(card.small_image, "trophy")
        self.assertEqual(card.small_text, "Sua maior sessão: 3 h 24 min")
        self.assertEqual(card.details, cards[0].details)                   # a linha 1 é a mesma dos outros
        activity = build_activity(card, self.target, self.cfg, pt, None, None)
        self.assertEqual(activity["state"], card.state)
        self.assertNotIn("achievement", [c.key for c in self.cards(None)])

    def test_options(self):
        self.cfg["show_achievement_card"] = False
        self.assertNotIn("achievement", [c.key for c in self.cards(unlock("owl"))])
        self.cfg["show_achievement_card"] = True
        stats = next(c for c in self.cards(unlock("owl")) if c.key == "stats")
        self.assertNotIn("Nível", stats.small_text)                       # o nível fica desligado por padrão
        self.cfg["show_level"] = True
        cards = self.cards(unlock("owl"))
        level = A.musician_level(A.total_points(self.results))[0]
        self.assertTrue(cards[-1].small_text.startswith(f"Nível {level} · "))
        stats = next(c for c in cards if c.key == "stats")
        self.assertIn(f"Nível {level}", stats.small_text)

    def test_fits_the_discord_limits(self):
        self.cfg["show_level"] = True
        for key in ("weekend_marathon", "collector", "backing"):
            card = self.cards(unlock(key, 1))[-1]
            activity = build_activity(card, self.target, self.cfg, en, None, None)
            for text in (activity["state"], activity["assets"]["small_text"]):
                self.assertLessEqual(len(text.encode("utf-16-le")) // 2, 128)


if __name__ == "__main__":
    unittest.main()
