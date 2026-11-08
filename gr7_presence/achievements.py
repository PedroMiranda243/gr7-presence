"""Conquistas: o catálogo, o cálculo a partir do histórico de prática e o registro do que já saiu.

O motor é puro (sem Tk e sem rede): recebe as sessões do `stats.json` e devolve, para cada conquista,
o nível alcançado e a data de cada nível. A data é a do dia em que a pessoa chegou lá, mesmo que o
programa só perceba depois, por exemplo na primeira vez depois de atualizar.

O `AchievementTracker` guarda em `dados\\conquistas.json` as marcas já destravadas. É por ele que um
aviso sai uma vez só e que uma conquista nunca volta atrás: mudar a meta diária ou perder o
`stats.json` não tira o que já foi ganho.

Conquista nova: uma linha no `CATALOG` e a sua medida em `collect_facts` (uma série em `series`, para
as de níveis, ou uma data em `singles`). Os pontos, o registro e as telas se ajustam sozinhos.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time as _time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Callable, Iterable

from .stats import MIN_SESSION_SECONDS, STREAK_DAY_SECONDS, day_totals, week_start

log = logging.getLogger(__name__)

LEVEL_POINTS = (10, 20, 40, 80, 150)   # Bronze, Prata, Ouro, Platina, Diamante
SINGLE_POINTS = 30
SECRET_POINTS = 50
CARD_SECONDS = 24 * 3600              # quanto tempo a conquista nova fica no cartão do Discord

ONE_DAY = timedelta(days=1)
DISTINCT_SECONDS = 60                 # um preset, amplificador ou gênero conta a partir de 1 minuto
FULL_MONTH_DAYS = 20                  # "Mês cheio": 20 dias tocados no mesmo mês
COMEBACK_DAYS = 8                     # "De volta": 7 dias inteiros sem tocar entre um dia e outro
RECORD_MIN = 3                        # "Superação" só vale contra um recorde de 3 dias ou mais
BASS_SECONDS = 3600
WEEKEND_MARATHON_SECONDS = 8 * 3600


@dataclass(frozen=True)
class Definition:
    """Uma conquista do catálogo. Com `levels`, é uma família em níveis (as marcas de cada nível, na
    unidade `unit`: "hours", "days" ou "count"); sem, é única (ou secreta, com `secret`)."""
    key: str
    group: str                         # practice, consistency, goal, tones, studio, collection, single, secret
    icon: str                          # nome do ícone no ui_kit
    levels: tuple[float, ...] | None = None
    unit: str = "count"
    secret: bool = False
    needs_goal: bool = False           # só existe com uma meta diária definida
    new_data: bool = False             # usa um dado que as sessões só gravam a partir da 1.5.0


CATALOG: tuple[Definition, ...] = (
    # prática
    Definition("hours", "practice", "clock", (10, 50, 100, 500, 1000), "hours"),
    Definition("sessions", "practice", "play", (10, 50, 100, 500, 1000)),
    Definition("days", "practice", "calendar", (10, 30, 100, 250, 500), "days"),
    Definition("marathon", "practice", "hourglass", (1, 2, 3, 4, 6), "hours"),
    Definition("long_day", "practice", "bolt", (2, 3, 4, 6, 8), "hours"),
    # constância
    Definition("streak", "consistency", "flame", (3, 7, 30, 100, 365), "days"),
    Definition("weekends", "consistency", "star", (1, 4, 12, 26, 52)),
    Definition("full_months", "consistency", "calendar", (1, 3, 6, 12)),
    # meta
    Definition("goal_days", "goal", "target", (5, 25, 100, 250, 500), "days", needs_goal=True),
    Definition("goal_weeks", "goal", "flag", (1, 4, 12, 26, 52), needs_goal=True),
    # timbres
    Definition("presets", "tones", "compass", (10, 25, 50, 100, 250)),
    Definition("amps", "tones", "amp", (3, 5, 10, 15, 20)),
    Definition("loyal", "tones", "heart", (1, 5, 10, 25, 50), "hours"),
    Definition("genres", "tones", "globe", (3, 5, 8, 12), new_data=True),
    Definition("own", "tones", "pen", (1, 5, 10, 25), new_data=True),
    # estúdio
    Definition("daw", "studio", "headphones", (1, 10, 50, 100), "hours"),
    Definition("backing", "studio", "note", (1, 10, 50, 100), "hours", new_data=True),
    # coleção: conta as marcas das outras
    Definition("collector", "collection", "trophy", (10, 25, 50, 75, 100)),
    # únicas
    Definition("first", "single", "play"),
    Definition("owl", "single", "moon"),
    Definition("early", "single", "sun"),
    Definition("perfect_week", "single", "star", needs_goal=True),
    Definition("comeback", "single", "return"),
    Definition("two_worlds", "single", "swap"),
    Definition("multi_daw", "single", "headphones"),
    Definition("one_year", "single", "gift"),
    Definition("record", "single", "trend"),
    Definition("bass", "single", "note", new_data=True),
    # secretas: aparecem como "?" até serem destravadas
    Definition("new_year", "secret", "star", secret=True),
    Definition("christmas", "secret", "gift", secret=True),
    Definition("friday13", "secret", "moon", secret=True),
    Definition("insomnia", "secret", "moon", secret=True),
    Definition("weekend_marathon", "secret", "bolt", secret=True),
)
BY_KEY = {d.key: d for d in CATALOG}
COLLECTOR = "collector"


@dataclass
class Facts:
    """Os números do histórico que as conquistas medem.

    `series`: por família, os pares (dia, valor) em que o valor cresceu, em ordem. O valor é acumulado
    (horas, sessões) ou recorde (maior sessão, maior sequência); a data de um nível é o primeiro dia
    em que o valor chegou à marca. `singles`: o primeiro dia de cada única e secreta, ou None."""
    today: date
    goal_minutes: int
    series: dict[str, list[tuple[date, float]]]
    singles: dict[str, date | None]


@dataclass(frozen=True)
class Result:
    """Como está uma conquista: o nível (0 = nenhum), a data de cada nível alcançado, o valor de hoje,
    a próxima marca (None no último nível) e o progresso até ela, de 0 a 1."""
    key: str
    definition: Definition
    level: int
    dates: tuple[date, ...]
    value: float
    next_target: float | None
    progress: float
    points: int

    @property
    def got(self) -> date | None:
        """O dia do nível mais alto alcançado."""
        return self.dates[-1] if self.dates else None

    @property
    def maxed(self) -> bool:
        return self.next_target is None

    def marks(self) -> list[tuple[str, int, date]]:
        """(marca, nível, dia) de cada nível alcançado: "hours:3" numa família, "owl" numa única."""
        if self.definition.levels:
            return [(f"{self.key}:{i}", i, d) for i, d in enumerate(self.dates, start=1)]
        return [(self.key, 1, d) for d in self.dates]


@dataclass(frozen=True)
class Unlock:
    """Uma marca destravada: o que o aviso, o cartão do Discord e a linha do tempo mostram."""
    mark: str
    key: str
    level: int
    got: date
    points: int


def mark_points(key: str, level: int) -> int:
    """Os pontos de uma marca: o do nível numa família, os fixos numa única ou secreta."""
    d = BY_KEY[key]
    if d.levels:
        return LEVEL_POINTS[level - 1]
    return SECRET_POINTS if d.secret else SINGLE_POINTS


def parse_mark(mark: str) -> tuple[str, int]:
    """"hours:3" -> ("hours", 3); "owl" -> ("owl", 1)."""
    key, _, level = mark.partition(":")
    return key, int(level) if level else 1


# ---- as medidas ---------------------------------------------------------------------------------------
def _dt(ts: float) -> datetime:
    return datetime.fromtimestamp(ts)


def _end(s: dict) -> float:
    return float(s.get("end") or s.get("start", 0) + s.get("seconds", 0))


def _end_date(s: dict) -> date:
    return _dt(_end(s)).date()


def _count(dates: Iterable[date]) -> list[tuple[date, float]]:
    return [(d, float(i)) for i, d in enumerate(dates, start=1)]


def _cumulative(pairs: Iterable[tuple[date, float]]) -> list[tuple[date, float]]:
    out, acc = [], 0.0
    for d, v in pairs:
        acc += v
        out.append((d, acc))
    return out


def _running_max(pairs: Iterable[tuple[date, float]]) -> list[tuple[date, float]]:
    out, best = [], 0.0
    for d, v in pairs:
        if v > best:
            best = v
            out.append((d, v))
    return out


def _seconds_by_name(s: dict, field: str) -> list[tuple[str, float]]:
    """Os pares (nome, segundos) de um campo da sessão, ignorando o que não for número."""
    data = s.get(field)
    if not isinstance(data, dict):
        return []
    return [(str(k), float(v)) for k, v in data.items() if isinstance(v, (int, float)) and v > 0]


def _distinct(sessions: list[dict], field: str) -> list[tuple[date, float]]:
    """Quantos nomes diferentes (presets, amplificadores, gêneros) já passaram de 1 minuto."""
    totals: Counter = Counter()
    out: list[tuple[date, float]] = []
    for s in sessions:
        for name, secs in _seconds_by_name(s, field):
            before = totals[name]
            totals[name] += secs
            if before < DISTINCT_SECONDS <= totals[name]:
                out.append((_end_date(s), float(len(out) + 1)))
    return out


def _loyal(sessions: list[dict]) -> list[tuple[date, float]]:
    """O maior tempo somado com um mesmo preset, em horas."""
    totals: Counter = Counter()
    pairs = []
    for s in sessions:
        names = _seconds_by_name(s, "presets")
        for name, secs in names:
            totals[name] += secs
        if names:
            pairs.append((_end_date(s), max(totals[n] for n, _ in names) / 3600))
    return _running_max(pairs)


def _window(sessions: list[dict], start_hour: int, end_hour: int) -> date | None:
    """O primeiro dia em que uma sessão passou pelo horário [start_hour, end_hour)."""
    first = None
    for s in sessions:
        st, en = _dt(s.get("start", 0)), _dt(_end(s))
        d = st.date()
        while d <= en.date():
            a, b = datetime.combine(d, time(start_hour)), datetime.combine(d, time(end_hour))
            if st < b and en > a:
                first = d if first is None else min(first, d)
                break
            d += ONE_DAY
    return first


def _streak_record(good: list[date]) -> date | None:
    """O dia em que uma sequência passou do maior recorde anterior (de 3 dias ou mais)."""
    best_done, run, prev = 0, 0, None
    for d in good:
        if prev is not None and d - prev == ONE_DAY:
            run += 1
        else:
            best_done, run = max(best_done, run), 1
        prev = d
        if best_done >= RECORD_MIN and run == best_done + 1:
            return d
    return None


def collect_facts(sessions: list[dict], today: date, goal_minutes: int = 0) -> Facts:
    """Os números de todas as conquistas, numa passada pelas sessões (as de 1 minuto ou mais)."""
    ss = sorted((s for s in sessions if isinstance(s, dict) and (s.get("seconds") or 0) >= MIN_SESSION_SECONDS),
                key=lambda s: s.get("start", 0))
    days = day_totals(ss)
    played = sorted(d for d, secs in days.items() if secs >= MIN_SESSION_SECONDS)
    good = sorted(d for d, secs in days.items() if secs >= STREAK_DAY_SECONDS)
    good_set = set(good)
    series: dict[str, list[tuple[date, float]]] = {}
    singles: dict[str, date | None] = {}

    # prática
    series["hours"] = _cumulative((d, days[d] / 3600) for d in sorted(days))
    series["sessions"] = _count(_dt(s.get("start", 0)).date() for s in ss)
    series["days"] = _count(good)
    series["marathon"] = _running_max((_end_date(s), s["seconds"] / 3600) for s in ss)
    series["long_day"] = _running_max((d, days[d] / 3600) for d in sorted(days))

    # constância
    runs, run, prev = [], 0, None
    for d in good:
        run = run + 1 if prev is not None and d - prev == ONE_DAY else 1
        prev = d
        runs.append((d, float(run)))
    series["streak"] = _running_max(runs)
    series["weekends"] = _count(d for d in good if d.weekday() == 6 and d - ONE_DAY in good_set)
    per_month: Counter = Counter()
    full = []
    for d in good:
        per_month[(d.year, d.month)] += 1
        if per_month[(d.year, d.month)] == FULL_MONTH_DAYS:
            full.append(d)
    series["full_months"] = _count(full)

    # meta: com a meta de hoje, como no painel das Estatísticas
    goal_days: list[date] = []
    if goal_minutes > 0:
        goal_days = [d for d in sorted(days) if days[d] >= goal_minutes * 60]
        series["goal_days"] = _count(goal_days)
        per_week: Counter = Counter()
        weeks = []
        for d in goal_days:
            per_week[week_start(d)] += 1
            if per_week[week_start(d)] == 5:
                weeks.append(d)
        series["goal_weeks"] = _count(weeks)

    # timbres
    series["presets"] = _distinct(ss, "presets")
    series["amps"] = _distinct(ss, "amps")
    series["genres"] = _distinct(ss, "genres")
    series["own"] = _distinct(ss, "own")
    series["loyal"] = _loyal(ss)

    # estúdio
    series["daw"] = _cumulative((_end_date(s), s["seconds"] / 3600) for s in ss if s.get("mode") == "plugin")
    series["backing"] = _cumulative((_end_date(s), float(s.get("backing") or 0) / 3600)
                                    for s in ss if isinstance(s.get("backing"), (int, float)) and s["backing"] > 0)

    # únicas
    singles["first"] = _dt(ss[0].get("start", 0)).date() if ss else None
    singles["owl"] = _window(ss, 0, 5)
    singles["early"] = _window(ss, 5, 7)
    singles["perfect_week"] = None
    if goal_days:
        goal_set = set(goal_days)
        singles["perfect_week"] = next((ws + timedelta(days=6) for ws in sorted({week_start(d) for d in goal_days})
                                        if all(ws + timedelta(days=i) in goal_set for i in range(7))), None)
    singles["comeback"] = next((b for a, b in zip(good, good[1:]) if (b - a).days >= COMEBACK_DAYS), None)
    modes: dict[date, set] = defaultdict(set)
    for s in ss:
        for iso in (s.get("days") or {_dt(s.get("start", 0)).date().isoformat(): 1}):
            try:
                modes[date.fromisoformat(iso)].add(s.get("mode"))
            except ValueError:
                pass
    singles["two_worlds"] = min((d for d, m in modes.items() if {"standalone", "plugin"} <= m), default=None)
    hosts: set[str] = set()
    singles["multi_daw"] = None
    for s in ss:
        if s.get("mode") == "plugin" and s.get("host"):
            hosts.add(str(s["host"]).casefold())
            if len(hosts) >= 2:
                singles["multi_daw"] = _dt(s.get("start", 0)).date()
                break
    year_after = singles["first"] + timedelta(days=365) if singles["first"] else None
    singles["one_year"] = next((d for d in good if d >= year_after), None) if year_after else None
    singles["record"] = _streak_record(good)
    singles["bass"] = None
    acc = 0.0
    for s in ss:
        acc += sum(secs for name, secs in _seconds_by_name(s, "sources") if name.casefold() == "bass")
        if acc >= BASS_SECONDS:
            singles["bass"] = _end_date(s)
            break

    # secretas
    singles["new_year"] = None
    for s in ss:
        st, en = _dt(s.get("start", 0)), _dt(_end(s))
        turn = next((datetime(y, 1, 1) for y in range(st.year + 1, en.year + 1) if st < datetime(y, 1, 1) < en), None)
        if turn:
            singles["new_year"] = turn.date()
            break
    singles["christmas"] = next((d for d in played if (d.month, d.day) in ((12, 24), (12, 25))), None)
    singles["friday13"] = next((d for d in played if d.day == 13 and d.weekday() == 4), None)
    singles["insomnia"] = None
    for s in ss:
        st, en = _dt(s.get("start", 0)), _dt(_end(s))
        after = datetime.combine(st.date() + ONE_DAY, time(3))
        if en >= after:
            singles["insomnia"] = after.date()
            break
    singles["weekend_marathon"] = next(
        (d for d in sorted(days) if d.weekday() == 6 and days.get(d - ONE_DAY, 0) + days[d] >= WEEKEND_MARATHON_SECONDS),
        None)
    return Facts(today, goal_minutes, series, singles)


# ---- o cálculo ----------------------------------------------------------------------------------------
def first_reach(series: list[tuple[date, float]], target: float) -> date | None:
    """O primeiro dia em que a série chegou a `target`."""
    return next((d for d, v in series if v >= target - 1e-9), None)


def _family(d: Definition, value: float, reached: list[date | None], permanent: dict[str, date]) -> Result:
    dates: list[date] = []
    for i, day in enumerate(reached, start=1):
        kept = permanent.get(f"{d.key}:{i}")
        if kept and (day is None or kept < day):
            day = kept
        if day is None:
            break
        dates.append(day)
    level = len(dates)
    nxt = d.levels[level] if level < len(d.levels) else None
    progress = 1.0 if nxt is None else max(0.0, min(1.0, value / nxt))
    return Result(d.key, d, level, tuple(dates), value, nxt, progress, sum(LEVEL_POINTS[:level]))


def _single(d: Definition, got: date | None) -> Result:
    if got is None:
        return Result(d.key, d, 0, (), 0.0, 1.0, 0.0, 0)
    return Result(d.key, d, 1, (got,), 1.0, None, 1.0, SECRET_POINTS if d.secret else SINGLE_POINTS)


def evaluate(facts: Facts, permanent: dict[str, date] | None = None) -> list[Result]:
    """Cada conquista do catálogo, na ordem dele. As de meta ficam de fora sem meta definida, a não ser
    que já tenham sido ganhas. `permanent`: as marcas já registradas (marca -> dia), que valem mesmo
    quando o histórico de hoje não chega mais lá."""
    permanent = {m: d for m, d in (permanent or {}).items() if parse_mark(m)[0] in BY_KEY}
    kept = {parse_mark(m)[0] for m in permanent}
    by_key: dict[str, Result] = {}
    for d in CATALOG:
        if d.key == COLLECTOR or (d.needs_goal and facts.goal_minutes <= 0 and d.key not in kept):
            continue
        if d.levels:
            series = facts.series.get(d.key, [])
            value = series[-1][1] if series else 0.0
            by_key[d.key] = _family(d, value, [first_reach(series, t) for t in d.levels], permanent)
        else:
            got = facts.singles.get(d.key)
            if d.key in permanent and (got is None or permanent[d.key] < got):
                got = permanent[d.key]
            by_key[d.key] = _single(d, got)
    marks = _count(sorted(day for r in by_key.values() for day in r.dates))
    coll = BY_KEY[COLLECTOR]
    by_key[COLLECTOR] = _family(coll, float(len(marks)), [first_reach(marks, t) for t in coll.levels], permanent)
    return [by_key[d.key] for d in CATALOG if d.key in by_key]


def total_points(results: list[Result]) -> int:
    return sum(r.points for r in results)


def unlocked_marks(results: list[Result]) -> int:
    return sum(r.level for r in results)


def total_marks(results: list[Result]) -> int:
    return sum(len(r.definition.levels) if r.definition.levels else 1 for r in results)


def musician_level(points: int) -> tuple[int, int, int]:
    """(nível, pontos já feitos dentro do nível, pontos que faltam para o próximo). O nível n começa em
    25·n·(n−1) pontos: o 2 em 50, o 5 em 500, o 10 em 2250."""
    level = 1
    while 25 * (level + 1) * level <= points:
        level += 1
    start, nxt = 25 * level * (level - 1), 25 * (level + 1) * level
    return level, points - start, nxt - points


# ---- o registro ---------------------------------------------------------------------------------------
class AchievementTracker:
    """O que já foi destravado, em `dados\\conquistas.json`, e a conta de hoje para as telas.

    O loop chama `maybe_check()` a cada passo (a conta roda a cada `every` segundos) e `check()` quando
    uma sessão termina. A janela lê `results()`, `unseen()` e `card()` de outra thread: tudo passa pela
    mesma trava."""

    def __init__(self, path: Path, stats, goal_minutes: Callable[[], int],
                 now: Callable[[], float] = _time.time, every: float = 60.0):
        self.path = Path(path)
        self.stats = stats
        self.goal_minutes = goal_minutes
        self.now = now
        self.every = every
        self.first_run_count = 0       # na primeira vez, quantas marcas o histórico já tinha
        self._lock = threading.Lock()
        self._unlocked: dict[str, dict] = {}     # marca -> {"got": "AAAA-MM-DD", "at": horário}
        self._unseen: list[str] = []
        self._card: dict | None = None
        self._results: list[Result] = []
        self._last_check: float | None = None
        self._fresh = True
        self._load()

    # ---- arquivo ----
    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            unlocked = data.get("unlocked", {})
            self._unlocked = {m: v for m, v in unlocked.items()
                              if isinstance(v, dict) and isinstance(v.get("got"), str) and parse_mark(m)[0] in BY_KEY}
            self._unseen = [m for m in data.get("unseen", []) if m in self._unlocked]
            card = data.get("card")
            self._card = card if isinstance(card, dict) and card.get("mark") in self._unlocked else None
            self._fresh = False
        except FileNotFoundError:
            self._fresh = True
        except (OSError, ValueError, AttributeError, TypeError) as exc:
            # Arquivo estragado: guarda uma cópia e recomeça em silêncio, como na primeira vez.
            backup = self.path.with_suffix(f".corrompido-{int(_time.time())}.json")
            log.error("conquistas.json ilegível (%s); guardando cópia em %s", exc, backup)
            try:
                os.replace(self.path, backup)
            except OSError:
                pass
            self._unlocked, self._unseen, self._card, self._fresh = {}, [], None, True

    def _save(self) -> None:
        with self._lock:
            payload = {"version": 1, "unlocked": dict(self._unlocked), "unseen": list(self._unseen),
                       "card": dict(self._card) if self._card else None}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            log.warning("Não consegui gravar as conquistas: %s", exc)

    def _permanent(self) -> dict[str, date]:
        out = {}
        for mark, info in self._unlocked.items():
            try:
                out[mark] = date.fromisoformat(info["got"])
            except ValueError:
                pass
        return out

    # ---- conta ----
    def _goal(self) -> int:
        try:
            return max(0, int(self.goal_minutes() or 0))
        except (TypeError, ValueError):     # meta escrita errada no config.json: fica sem meta
            return 0

    def check(self, today: date | None = None) -> list[Unlock]:
        """Refaz a conta e devolve as marcas novas, na ordem do catálogo. Na primeira vez (sem arquivo),
        o que o histórico já tinha entra como visto, sem aviso, e `first_run_count` diz quantas eram."""
        facts = collect_facts(self.stats.snapshot(), today or date.today(), self._goal())
        now = self.now()
        with self._lock:
            permanent = self._permanent()
        results = evaluate(facts, permanent)
        reached = [Unlock(m, r.key, level, day, mark_points(r.key, level))
                   for r in results for m, level, day in r.marks()]
        with self._lock:
            new = [u for u in reached if u.mark not in self._unlocked]
            for u in new:
                self._unlocked[u.mark] = {"got": u.got.isoformat(), "at": now}
            first = self._fresh
            if first:
                self.first_run_count = len(self._unlocked)
                self._fresh = False
                announced: list[Unlock] = []
            else:
                announced = new
                self._unseen += [u.mark for u in new if u.mark not in self._unseen]
                if new:
                    best = max(new, key=lambda u: (u.got, u.points))
                    self._card = {"mark": best.mark, "until": now + CARD_SECONDS}
            self._results = results
            self._last_check = now
        if new or first:
            self._save()
        for u in announced:
            log.info("Conquista nova: %s (nível %d, %s)", u.key, u.level, u.got.isoformat())
        return announced

    def maybe_check(self, today: date | None = None) -> list[Unlock]:
        """`check()` se já passaram `every` segundos desde a última conta."""
        if self._last_check is not None and self.now() - self._last_check < self.every:
            return []
        return self.check(today)

    # ---- para as telas ----
    def results(self) -> list[Result]:
        """A última conta, com as marcas registradas somadas (vazia antes da primeira conta)."""
        with self._lock:
            return list(self._results)

    def unseen(self) -> set[str]:
        """As marcas destravadas que a pessoa ainda não viu na página Conquistas."""
        with self._lock:
            return set(self._unseen)

    def mark_seen(self) -> None:
        with self._lock:
            changed = bool(self._unseen)
            self._unseen = []
        if changed:
            self._save()

    def card(self) -> Unlock | None:
        """A conquista do cartão do Discord, enquanto não passaram 24 h."""
        with self._lock:
            card = self._card
            info = self._unlocked.get(card["mark"]) if card else None
        if not card or not info or self.now() >= float(card.get("until", 0)):
            return None
        key, level = parse_mark(card["mark"])
        try:
            got = date.fromisoformat(info["got"])
        except ValueError:
            return None
        return Unlock(card["mark"], key, level, got, mark_points(key, level))

    def timeline(self) -> list[Unlock]:
        """Todas as marcas destravadas, da mais nova para a mais antiga (pelo dia em que saíram)."""
        with self._lock:
            items = list(self._unlocked.items())
        out = []
        for mark, info in items:
            key, level = parse_mark(mark)
            try:
                out.append(Unlock(mark, key, level, date.fromisoformat(info["got"]), mark_points(key, level)))
            except (ValueError, KeyError, IndexError):
                pass
        order = {d.key: i for i, d in enumerate(CATALOG)}
        return sorted(out, key=lambda u: (u.got, order.get(u.key, 0), u.level), reverse=True)
