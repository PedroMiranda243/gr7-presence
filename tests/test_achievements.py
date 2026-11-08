import json
import tempfile
import time as _time
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path

from gr7_presence import achievements as A
from gr7_presence.stats import Stats


def session(start: datetime, minutes: float, mode: str = "standalone", host: str | None = None,
            presets: dict | None = None, amps: dict | None = None, **extra) -> dict:
    """Uma sessão como as do stats.json, com o tempo dividido entre os dias do relógio."""
    secs = minutes * 60
    end = start + timedelta(seconds=secs)
    days: dict[str, float] = {}
    t = start
    while t < end:
        nxt = min(end, datetime.combine(t.date() + timedelta(days=1), time()))
        days[t.date().isoformat()] = days.get(t.date().isoformat(), 0.0) + (nxt - t).total_seconds()
        t = nxt
    s = {"start": start.timestamp(), "end": end.timestamp(), "seconds": secs, "mode": mode, "host": host,
         "days": days, "presets": presets or {}, "amps": amps or {}}
    s.update(extra)
    return s


def daily(first: date, n: int, minutes: float = 60, hour: int = 20, **kw) -> list[dict]:
    """`n` dias seguidos tocando `minutes` minutos, às `hour` horas."""
    return [session(datetime.combine(first + timedelta(days=i), time(hour)), minutes, **kw) for i in range(n)]


def results(sessions, today=date(2026, 12, 31), goal=0, permanent=None) -> dict[str, A.Result]:
    facts = A.collect_facts(sessions, today, goal)
    return {r.key: r for r in A.evaluate(facts, permanent)}


JAN = date(2026, 1, 1)   # uma quinta-feira


class CatalogTest(unittest.TestCase):
    def test_shape(self):
        keys = [d.key for d in A.CATALOG]
        self.assertEqual(len(keys), 33)
        self.assertEqual(len(set(keys)), 33)
        families = [d for d in A.CATALOG if d.levels]
        self.assertEqual(len(families), 18)
        self.assertEqual(sum(1 for d in A.CATALOG if not d.levels and not d.secret), 10)
        self.assertEqual(sum(1 for d in A.CATALOG if d.secret), 5)
        for d in families:
            self.assertEqual(list(d.levels), sorted(set(d.levels)), d.key)      # marcas crescentes
            self.assertIn(len(d.levels), (4, 5), d.key)
            self.assertIn(d.unit, ("hours", "days", "count"))
        self.assertEqual(sum(len(d.levels) if d.levels else 1 for d in A.CATALOG), 100)

    def test_marks_and_points(self):
        self.assertEqual(A.parse_mark("hours:3"), ("hours", 3))
        self.assertEqual(A.parse_mark("owl"), ("owl", 1))
        self.assertEqual(A.mark_points("hours", 5), 150)
        self.assertEqual(A.mark_points("owl", 1), A.SINGLE_POINTS)
        self.assertEqual(A.mark_points("new_year", 1), A.SECRET_POINTS)

    def test_musician_level(self):
        self.assertEqual(A.musician_level(0), (1, 0, 50))
        self.assertEqual(A.musician_level(49), (1, 49, 1))
        self.assertEqual(A.musician_level(50), (2, 0, 100))
        self.assertEqual(A.musician_level(500)[0], 5)
        self.assertEqual(A.musician_level(2250)[0], 10)
        everything = sum(sum(A.LEVEL_POINTS[:len(d.levels)]) if d.levels else
                         (A.SECRET_POINTS if d.secret else A.SINGLE_POINTS) for d in A.CATALOG)
        self.assertIn(A.musician_level(everything)[0], (13, 14, 15))       # tudo destravado: perto do 14


class PracticeTest(unittest.TestCase):
    def test_twelve_days_of_one_hour(self):
        r = results(daily(JAN, 12))
        self.assertEqual((r["hours"].level, r["hours"].dates), (1, (JAN + timedelta(days=9),)))
        self.assertEqual(r["sessions"].dates, (JAN + timedelta(days=9),))
        self.assertEqual(r["days"].dates, (JAN + timedelta(days=9),))
        self.assertEqual(r["marathon"].dates, (JAN,))                          # 1 h
        self.assertEqual(r["long_day"].level, 0)
        self.assertEqual(r["streak"].dates, (JAN + timedelta(days=2), JAN + timedelta(days=6)))   # 3 e 7
        self.assertEqual(r["streak"].value, 12)
        self.assertEqual(r["weekends"].dates, (date(2026, 1, 4),))             # sábado 3 e domingo 4
        self.assertEqual(r["weekends"].value, 2)
        self.assertEqual(r["hours"].next_target, 50)
        self.assertAlmostEqual(r["hours"].progress, 12 / 50)
        self.assertEqual(r["hours"].points, 10)

    def test_marathon_and_long_day(self):
        r = results([session(datetime(2026, 3, 2, 14), 210)])                 # 3 h 30 numa sessão
        self.assertEqual(r["marathon"].level, 3)
        self.assertEqual(r["long_day"].level, 2)
        self.assertEqual(r["marathon"].next_target, 4)

    def test_full_month(self):
        r = results(daily(date(2026, 2, 1), 20, minutes=10))
        self.assertEqual(r["full_months"].dates, (date(2026, 2, 20),))

    def test_short_sessions_do_not_count(self):
        r = results([session(datetime(2026, 1, 1, 20), 0.5)])                 # 30 segundos
        self.assertEqual(r["first"].level, 0)
        self.assertEqual(r["sessions"].value, 0)


class GoalTest(unittest.TestCase):
    def test_goal_families_and_perfect_week(self):
        sunday = date(2026, 1, 4)
        r = results(daily(sunday, 7, minutes=40), goal=30)
        self.assertEqual(r["goal_days"].dates, (sunday + timedelta(days=4),))     # o 5º dia
        self.assertEqual(r["goal_weeks"].dates, (sunday + timedelta(days=4),))
        self.assertEqual(r["perfect_week"].dates, (sunday + timedelta(days=6),))  # o sábado

    def test_no_goal_no_goal_achievements(self):
        r = results(daily(date(2026, 1, 4), 7, minutes=40), goal=0)
        self.assertNotIn("goal_days", r)
        self.assertNotIn("perfect_week", r)

    def test_kept_marks_survive(self):
        """Uma marca já registrada vale mesmo com a meta mais alta (ou sem meta)."""
        sessions = daily(date(2026, 1, 4), 7, minutes=40)
        kept = {"goal_days:1": date(2026, 1, 8), "goal_days:2": date(2026, 2, 1)}
        r = results(sessions, goal=60, permanent=kept)
        self.assertEqual(r["goal_days"].level, 2)
        self.assertEqual(r["goal_days"].dates, (date(2026, 1, 8), date(2026, 2, 1)))
        self.assertIn("goal_days", results(sessions, goal=0, permanent=kept))


class TonesAndStudioTest(unittest.TestCase):
    def test_distinct_presets_and_amps(self):
        sessions = [session(datetime(2026, 1, 1 + i, 20), 30, presets={f"P{i}": 1500},
                            amps={f"A{i % 4}": 1500}) for i in range(12)]
        sessions[0]["presets"]["Mini"] = 20                      # 20 segundos no total
        r = results(sessions)
        self.assertEqual(r["presets"].value, 12)                 # "Mini" (20 s) não conta
        self.assertEqual(r["presets"].dates, (date(2026, 1, 10),))
        self.assertEqual(r["amps"].value, 4)
        self.assertEqual(r["amps"].dates, (date(2026, 1, 3),))   # o 3º amplificador

    def test_loyal(self):
        sessions = daily(JAN, 6, presets={"Clean Cristalino": 3600})
        self.assertEqual(results(sessions)["loyal"].dates, (JAN, JAN + timedelta(days=4)))   # 1 h e 5 h
        self.assertEqual(results(sessions)["loyal"].value, 6)

    def test_new_data_counts_only_where_recorded(self):
        old = daily(JAN, 5)                                           # sessões antigas, sem os campos novos
        new = [session(datetime(2026, 2, 1, 20), 120, presets={"Meu": 7200}, own={"Meu": 7200},
                       genres={"Rock": 3000, "Metal": 3000, "Funk & Soul": 1200}, sources={"Bass": 7200},
                       backing=4000)]
        r = results(old)
        self.assertEqual((r["genres"].value, r["own"].value, r["backing"].value, r["bass"].level), (0, 0, 0, 0))
        r = results(old + new)
        self.assertEqual(r["genres"].dates, (date(2026, 2, 1),))
        self.assertEqual(r["own"].dates, (date(2026, 2, 1),))
        self.assertEqual(r["backing"].dates, (date(2026, 2, 1),))     # 1 h 06
        self.assertEqual(r["bass"].dates, (date(2026, 2, 1),))
        self.assertTrue(A.BY_KEY["genres"].new_data)

    def test_studio(self):
        sessions = [session(datetime(2026, 1, 1, 10), 40),
                    session(datetime(2026, 1, 1, 20), 40, mode="plugin", host="REAPER"),
                    session(datetime(2026, 1, 3, 20), 30, mode="plugin", host="reaper"),
                    session(datetime(2026, 1, 5, 20), 30, mode="plugin", host="FL Studio")]
        r = results(sessions)
        self.assertEqual(r["two_worlds"].dates, (JAN,))
        self.assertEqual(r["multi_daw"].dates, (date(2026, 1, 5),))   # "reaper" é o mesmo REAPER
        self.assertEqual(r["daw"].dates, (date(2026, 1, 3),))         # 40 + 30 min: passou de 1 h
        self.assertAlmostEqual(r["daw"].value, 100 / 60)


class SinglesAndSecretsTest(unittest.TestCase):
    def test_owl_and_early(self):
        r = results([session(datetime(2026, 3, 1, 23, 30), 60)])
        self.assertEqual(r["owl"].dates, (date(2026, 3, 2),))         # passou da meia-noite
        self.assertEqual(r["early"].level, 0)
        r = results([session(datetime(2026, 3, 1, 22), 115)])         # até 23:55: ainda não é coruja
        self.assertEqual(r["owl"].level, 0)
        r = results([session(datetime(2026, 3, 1, 5, 30), 30)])
        self.assertEqual(r["early"].dates, (date(2026, 3, 1),))

    def test_comeback_needs_a_week_off(self):
        r = results(daily(JAN, 1) + daily(date(2026, 1, 9), 1))       # 7 dias inteiros sem tocar
        self.assertEqual(r["comeback"].dates, (date(2026, 1, 9),))
        r = results(daily(JAN, 1) + daily(date(2026, 1, 8), 1))
        self.assertEqual(r["comeback"].level, 0)

    def test_record(self):
        r = results(daily(JAN, 3) + daily(date(2026, 1, 10), 4))
        self.assertEqual(r["record"].dates, (date(2026, 1, 13),))     # passou dos 3 dias
        r = results(daily(JAN, 2) + daily(date(2026, 1, 10), 3))      # recorde de 2 não vale
        self.assertEqual(r["record"].level, 0)

    def test_one_year(self):
        r = results(daily(date(2025, 1, 5), 1) + daily(date(2026, 1, 6), 1))
        self.assertEqual(r["one_year"].dates, (date(2026, 1, 6),))
        self.assertEqual(r["first"].dates, (date(2025, 1, 5),))

    def test_secrets(self):
        r = results([session(datetime(2025, 12, 31, 23, 30), 50)])    # passou da virada
        self.assertEqual(r["new_year"].dates, (date(2026, 1, 1),))
        self.assertEqual(r["new_year"].points, A.SECRET_POINTS)
        self.assertEqual(results(daily(date(2026, 12, 24), 1))["christmas"].dates, (date(2026, 12, 24),))
        self.assertEqual(results(daily(date(2026, 2, 13), 1))["friday13"].dates, (date(2026, 2, 13),))
        self.assertEqual(results(daily(date(2026, 4, 13), 1))["friday13"].level, 0)   # segunda-feira, 13
        r = results([session(datetime(2026, 3, 1, 23), 270)])          # 23:00 até 03:30
        self.assertEqual(r["insomnia"].dates, (date(2026, 3, 2),))
        r = results([session(datetime(2026, 3, 2, 0, 30), 180)])       # começou depois da meia-noite
        self.assertEqual(r["insomnia"].level, 0)
        saturday = date(2026, 1, 3)
        r = results([session(datetime.combine(saturday, time(13)), 270),
                     session(datetime.combine(saturday + timedelta(days=1), time(13)), 240)])
        self.assertEqual(r["weekend_marathon"].dates, (saturday + timedelta(days=1),))

    def test_collector_counts_the_others(self):
        r = results(daily(JAN, 12))
        others = sum(x.level for k, x in r.items() if k != "collector")
        self.assertEqual(r["collector"].value, others)
        self.assertEqual(r["collector"].level, 1 if others >= 10 else 0)

    def test_speed(self):
        """Cinco anos tocando todo dia, com presets e amplificadores: a conta roda a cada minuto."""
        sessions = [session(datetime.combine(date(2021, 1, 1) + timedelta(days=i), time(20)), 50,
                            presets={f"P{i % 80}": 2000, f"Q{i % 7}": 1000}, amps={f"A{i % 15}": 3000},
                            genres={"Rock": 3000}, backing=600)
                    for i in range(5 * 365)]
        best = min(self._time(sessions) for _ in range(3))
        # No PC do dono do projeto, ~25 ms; a folga cobre a máquina mais lenta da CI.
        self.assertLess(best, 0.25)

    @staticmethod
    def _time(sessions) -> float:
        t0 = _time.perf_counter()
        A.evaluate(A.collect_facts(sessions, date(2026, 1, 1), 30))
        return _time.perf_counter() - t0


class TrackerTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.stats = Stats(self.base / "stats.json")
        self.clock = [1_800_000_000.0]
        self.goal = 0

    def tracker(self) -> A.AchievementTracker:
        return A.AchievementTracker(self.base / "conquistas.json", self.stats, lambda: self.goal,
                                    now=lambda: self.clock[0])

    def test_first_time_is_quiet(self):
        self.stats.sessions = daily(JAN, 12)
        t = self.tracker()
        self.assertEqual(t.check(date(2026, 2, 1)), [])
        self.assertGreater(t.first_run_count, 5)
        self.assertEqual(t.unseen(), set())
        self.assertIsNone(t.card())
        self.assertTrue((self.base / "conquistas.json").exists())
        self.assertEqual(A.unlocked_marks(t.results()), t.first_run_count)

    def test_new_marks_are_announced_once(self):
        self.stats.sessions = daily(JAN, 6)
        t = self.tracker()
        t.check(date(2026, 2, 1))
        self.stats.sessions += daily(date(2026, 1, 7), 1)               # 7 dias seguidos
        new = t.check(date(2026, 2, 1))
        self.assertIn("streak:2", [u.mark for u in new])
        self.assertIn("streak:2", t.unseen())
        card = t.card()
        self.assertIsNotNone(card)
        self.assertEqual(t.check(date(2026, 2, 1)), [])                 # nada de novo
        again = self.tracker()                                          # o programa reabriu
        self.assertEqual(again.check(date(2026, 2, 1)), [])
        self.assertIn("streak:2", again.unseen())
        self.clock[0] += A.CARD_SECONDS + 1
        self.assertIsNone(again.card())                                 # o cartão vale 24 h
        again.mark_seen()
        self.assertEqual(self.tracker().unseen(), set())

    def test_marks_are_permanent(self):
        self.goal = 30
        self.stats.sessions = daily(date(2026, 1, 4), 7, minutes=40)
        t = self.tracker()
        t.check(date(2026, 2, 1))
        self.goal = 120                                                 # meta mais alta: o histórico não chega
        t.check(date(2026, 2, 1))
        r = {x.key: x for x in t.results()}
        self.assertEqual(r["goal_days"].level, 1)
        self.assertEqual(r["perfect_week"].level, 1)
        self.stats.sessions = []                                        # até sem histórico
        t.check(date(2026, 2, 1))
        self.assertEqual({x.key: x for x in t.results()}["streak"].level, 2)

    def test_broken_file_starts_quietly(self):
        (self.base / "conquistas.json").write_text("{não é json", encoding="utf-8")
        self.stats.sessions = daily(JAN, 12)
        t = self.tracker()
        self.assertEqual(t.check(date(2026, 2, 1)), [])
        self.assertTrue(list(self.base.glob("conquistas.corrompido-*.json")))
        json.loads((self.base / "conquistas.json").read_text(encoding="utf-8"))

    def test_check_every_minute(self):
        self.stats.sessions = daily(JAN, 6)
        t = self.tracker()
        t.maybe_check(date(2026, 2, 1))
        self.stats.sessions += daily(date(2026, 1, 7), 1)
        self.clock[0] += 30
        self.assertEqual(t.maybe_check(date(2026, 2, 1)), [])          # ainda não deu um minuto
        self.clock[0] += 31
        self.assertIn("streak:2", [u.mark for u in t.maybe_check(date(2026, 2, 1))])

    def test_timeline_newest_first(self):
        self.stats.sessions = daily(JAN, 12)
        t = self.tracker()
        t.check(date(2026, 2, 1))
        days = [u.got for u in t.timeline()]
        self.assertEqual(days, sorted(days, reverse=True))
        self.assertEqual(len(days), t.first_run_count)


if __name__ == "__main__":
    unittest.main()
