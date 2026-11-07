"""Histórico de prática: sessões, tempo por dia, por preset e por amplificador."""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

MIN_SESSION_SECONDS = 60     # sessões menores que isso são descartadas
STREAK_DAY_SECONDS = 5 * 60  # um dia conta para a sequência com 5 min de prática
MAX_TICK_SECONDS = 30        # protege contra saltos (PC suspenso, relógio alterado)


@dataclass
class Summary:
    today: float
    week: float
    total: float
    sessions: int
    streak: int
    best_streak: int
    top_presets: list[tuple[str, float]]
    top_amps: list[tuple[str, float]]
    recent: list[dict]


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts).date().isoformat()


def _streaks(days: dict[str, float], today: date) -> tuple[int, int]:
    good = {date.fromisoformat(d) for d, secs in days.items() if secs >= STREAK_DAY_SECONDS}
    # Sequência atual: termina hoje ou, se hoje ainda não conta, ontem.
    cursor = today if today in good else today - timedelta(days=1)
    current = 0
    while cursor in good:
        current += 1
        cursor -= timedelta(days=1)
    best = run = 0
    prev = None
    for d in sorted(good):
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        best = max(best, run)
        prev = d
    return current, best


class Stats:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.sessions: list[dict] = []
        self.current: dict | None = None
        self._lock = threading.Lock()
        self._last_save = 0.0
        self._tick_at = time.time()
        self._load()

    # ---- persistência --------------------------------------------------------------------
    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.sessions = [s for s in data.get("sessions", []) if isinstance(s, dict)]
        except FileNotFoundError:
            self.sessions = []
        except (OSError, ValueError) as exc:
            backup = self.path.with_suffix(f".corrompido-{int(time.time())}.json")
            log.error("stats.json ilegível (%s); guardando cópia em %s", exc, backup)
            try:
                os.replace(self.path, backup)
            except OSError:
                pass
            self.sessions = []

    def save(self) -> None:
        with self._lock:
            sessions = list(self.sessions)
            if self.current and self.current["seconds"] >= MIN_SESSION_SECONDS:
                sessions.append(dict(self.current))
            payload = {"version": 1, "sessions": sessions}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.path)
        self._last_save = time.time()

    def save_if_due(self, every: float = 60.0) -> None:
        if self.current and time.time() - self._last_save >= every:
            self.save()

    # ---- sessão --------------------------------------------------------------------------
    def start(self, started_at: float, mode: str, host: str | None = None) -> None:
        with self._lock:
            self.current = {
                "start": started_at, "end": started_at, "seconds": 0.0, "mode": mode, "host": host,
                "days": {}, "presets": {}, "amps": {}, "last_preset": None, "last_amp": None,
            }
        self._tick_at = time.time()
        log.info("Sessão iniciada (%s%s)", mode, f" em {host}" if host else "")

    def tick(self, preset: str | None, amp: str | None, now: float | None = None) -> None:
        if not self.current:
            return
        now = now or time.time()
        dt = min(max(0.0, now - self._tick_at), MAX_TICK_SECONDS)
        self._tick_at = now
        with self._lock:
            cur = self.current
            cur["seconds"] += dt
            cur["end"] = now
            day = _day(now)
            cur["days"][day] = cur["days"].get(day, 0.0) + dt
            if preset:
                cur["presets"][preset] = cur["presets"].get(preset, 0.0) + dt
                cur["last_preset"] = preset
            if amp:
                cur["amps"][amp] = cur["amps"].get(amp, 0.0) + dt
                cur["last_amp"] = amp

    def end(self) -> None:
        with self._lock:
            cur, self.current = self.current, None
            if cur and cur["seconds"] >= MIN_SESSION_SECONDS:
                self.sessions.append(cur)
                log.info("Sessão encerrada: %.0f s", cur["seconds"])
            elif cur:
                log.info("Sessão curta (%.0f s) descartada", cur["seconds"])
        self.save()

    # ---- números -------------------------------------------------------------------------
    def snapshot(self) -> list[dict]:
        """Cópia de todas as sessões, com a que está acontecendo agora no fim."""
        with self._lock:
            return list(self.sessions) + ([dict(self.current)] if self.current else [])

    def summary(self, top: int = 5, recent: int = 8, today: date | None = None) -> Summary:
        today = today or date.today()
        with self._lock:
            sessions = list(self.sessions) + ([dict(self.current)] if self.current else [])
        days: Counter = Counter()
        presets: Counter = Counter()
        amps: Counter = Counter()
        for s in sessions:
            days.update(s.get("days") or {_day(s.get("start", 0)): s.get("seconds", 0)})
            presets.update(s.get("presets") or {})
            amps.update(s.get("amps") or {})
        week_start = today - timedelta(days=6)
        week = sum(v for d, v in days.items() if week_start <= date.fromisoformat(d) <= today)
        streak, best = _streaks(dict(days), today)
        return Summary(
            today=days.get(today.isoformat(), 0.0),
            week=week,
            total=sum(days.values()),
            sessions=len(sessions),
            streak=streak,
            best_streak=best,
            top_presets=presets.most_common(top),
            top_amps=amps.most_common(top),
            recent=sorted(sessions, key=lambda s: s.get("start", 0), reverse=True)[:recent],
        )


# ---- números para a página de estatísticas ---------------------------------------------------------
@dataclass
class Bar:
    start: date        # o dia, o domingo da semana ou o dia 1 do mês
    seconds: float
    current: bool      # hoje, esta semana ou este mês


@dataclass
class Achievement:
    key: str           # streak7, hours10, goal_week, streak30, hours100
    target: int        # dias, horas ou dias da semana com a meta
    got: date | None   # o dia em que foi conquistada
    value: float       # recorde de dias, horas tocadas ou dias com a meta nesta semana
    progress: float    # de 0 a 1


def day_totals(sessions: list[dict]) -> dict[date, float]:
    """Segundos tocados por dia."""
    days: Counter = Counter()
    for s in sessions:
        days.update(s.get("days") or {_day(s.get("start", 0)): s.get("seconds", 0)})
    return {date.fromisoformat(d): secs for d, secs in days.items()}


def week_start(d: date) -> date:
    """O domingo da semana, como nas colunas do calendário."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _month_start(d: date, back: int = 0) -> date:
    index = d.year * 12 + d.month - 1 - back
    return date(index // 12, index % 12 + 1, 1)


def period_start(today: date, period: str) -> date | None:
    """Primeiro dia que conta no período: "days" (14 dias), "weeks" (16 semanas) ou "all"."""
    if period == "days":
        return today - timedelta(days=13)
    if period == "weeks":
        return week_start(today) - timedelta(weeks=15)
    return None


def period_bars(days: dict[date, float], today: date, period: str) -> list[Bar]:
    """Barras do gráfico: 14 dias, 16 semanas ou os últimos 12 meses (em "all")."""
    if period == "days":
        return [Bar(d, days.get(d, 0.0), d == today) for d in (today - timedelta(days=13 - i) for i in range(14))]
    if period == "weeks":
        first = week_start(today) - timedelta(weeks=15)
        bars = []
        for i in range(16):
            start = first + timedelta(weeks=i)
            secs = sum(v for d, v in days.items() if start <= d < start + timedelta(weeks=1))
            bars.append(Bar(start, secs, i == 15))
        return bars
    bars = []
    for back in range(11, -1, -1):
        start = _month_start(today, back)
        secs = sum(v for d, v in days.items() if (d.year, d.month) == (start.year, start.month))
        bars.append(Bar(start, secs, back == 0))
    return bars


def top_in(sessions: list[dict], field: str, since: date | None, n: int = 5) -> list[tuple[str, float]]:
    """Os `n` presets (field="presets") ou amplificadores ("amps") mais tocados desde `since`."""
    total: Counter = Counter()
    for s in sessions:
        if since is None or datetime.fromtimestamp(s.get("start", 0)).date() >= since:
            total.update(s.get(field) or {})
    return total.most_common(n)


def sessions_since(sessions: list[dict], since: date) -> int:
    return sum(1 for s in sessions if datetime.fromtimestamp(s.get("start", 0)).date() >= since)


def achievements(days: dict[date, float], today: date, goal_minutes: int) -> list[Achievement]:
    """As conquistas, na ordem da tela. A da meta só existe com uma meta diária definida."""
    good = sorted(d for d, secs in days.items() if secs >= STREAK_DAY_SECONDS)
    _current, best = _streaks({d.isoformat(): days[d] for d in days}, today)

    def streak_reached(n: int) -> date | None:
        run, prev = 0, None
        for d in good:
            run = run + 1 if prev and d - prev == timedelta(days=1) else 1
            prev = d
            if run >= n:
                return d
        return None

    def hours_reached(hours: int) -> date | None:
        acc = 0.0
        for d in sorted(days):
            acc += days[d]
            if acc >= hours * 3600:
                return d
        return None

    total_h = sum(days.values()) / 3600
    out = [
        Achievement("streak7", 7, streak_reached(7), best, min(1.0, best / 7)),
        Achievement("hours10", 10, hours_reached(10), total_h, min(1.0, total_h / 10)),
    ]
    if goal_minutes > 0:
        per_week: Counter = Counter()
        first = None
        for d in sorted(days):
            if days[d] >= goal_minutes * 60:
                per_week[week_start(d)] += 1
                if per_week[week_start(d)] == 5 and first is None:
                    first = d
        this_week = per_week[week_start(today)]
        out.append(Achievement("goal_week", 5, first, this_week, min(1.0, this_week / 5)))
    out += [
        Achievement("streak30", 30, streak_reached(30), best, min(1.0, best / 30)),
        Achievement("hours100", 100, hours_reached(100), total_h, min(1.0, total_h / 100)),
    ]
    return out
