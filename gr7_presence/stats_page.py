"""Página Estatísticas da janela principal, desenhada pelo Pillow como no exemplo aprovado (Palco).

De cima para baixo: o gráfico com a luz na barra de hoje e os números ao lado; as conquistas; o
calendário de 16 semanas e os presets mais tocados; os amplificadores e as sessões recentes.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Callable

from . import ui_kit as K
from .i18n import Translator, format_time
from .stats import (Achievement, Bar, Stats, achievements, day_totals, period_bars, period_start,
                    sessions_since, top_in, week_start)

PAD_X, PAD_TOP, PAD_BOTTOM, GAP = 24, 20, 24, 14
CHART_H, FACTS_W = 232, 230
PERIODS = ("days", "weeks", "all")

TITLE = K.Style(30, 800, K.TEXT, display=True, width=125, line=1.0)
H3 = K.Style(15, 700, K.TEXT, display=True, width=112, line=1.2)
FACT_BIG = K.Style(24, 800, K.GLOW, display=True, width=118, line=1.05)
FACT = K.Style(14, 400, K.TEXT_SOFT, line=1.45)
ROW = K.Style(13, 400, K.TEXT, line=1.4)
ROW_SOFT = K.Style(13, 400, K.TEXT_SOFT, line=1.4)
ROW_MUTED = K.Style(13, 400, K.MUTED, line=1.4)
LIVE = K.Style(13, 600, K.GREEN, line=1.4)
EMPTY = K.Style(13.5, 400, K.MUTED, line=1.5)
AXIS = K.Style(11, 400, K.FAINT)
AXIS_NOW = K.Style(11, 700, K.AMBER)
GOAL = K.Style(11, 600, K.AMBER)
VALUE = K.Style(12, 700, K.GLOW)
CAL = K.Style(10.5, 400, K.FAINT, line=1.0)
LEGEND = K.Style(11.5, 400, K.FAINT)
BADGE_TITLE = K.Style(12.5, 600, K.TEXT, line=1.3)
BADGE_SUB = K.Style(12, 400, K.TEXT_SOFT, line=1.3)

BADGE_ICONS = {"streak7": "flame", "hours10": "clock", "goal_week": "target", "streak30": "flame", "hours100": "clock"}
LIGHT = [(0.0, (255, 179, 71, 0.32)), (0.55, (255, 106, 61, 0.12)), (1.0, (17, 19, 26, 0.0))]
ROW_H = 6 + 13 * 1.4 + 6
REC_H = 7 + 13 * 1.4 + 7
CAL_CELL, CAL_GAP, CAL_LEFT, CAL_TOP = 13, 4, 20, 18


def level(seconds: float) -> int:
    """Tom do calendário: as mesmas faixas do exemplo (até 20, 45, 75 minutos e mais)."""
    m = seconds / 60
    return 0 if seconds <= 0 else 1 if m <= 20 else 2 if m <= 45 else 3 if m <= 75 else 4


def nice_ticks(peak_minutes: float) -> tuple[list[int], float]:
    """Linhas do gráfico em passos redondos (30 min, 1 h, 2 h…) e o topo com um pouco de folga."""
    for step in (15, 30, 60, 120, 180, 300, 600, 900, 1200, 1800, 3000, 6000, 12000):
        if peak_minutes / step <= 3.2:
            break
    count = max(1, math.ceil(peak_minutes / step - 1e-9))
    ticks = [step * i for i in range(count + 1)]
    return ticks, max(peak_minutes, ticks[-1]) * 1.1


class StatsPage:
    key = "stats"
    icon = "chart"
    label_key = "nav_stats"

    def __init__(self, stats: Stats, goal_minutes: Callable[[], int], today: Callable[[], date] = date.today):
        self.stats = stats
        self.goal_minutes = goal_minutes
        self.today = today
        self.period = "days"
        self.on_change: Callable[[], None] = lambda: None

    def set_period(self, period: str) -> None:
        if period != self.period:
            self.period = period
            self.on_change()

    # ---- dados -------------------------------------------------------------------------------
    def _collect(self) -> dict:
        today = self.today()
        sessions = self.stats.snapshot()
        days = day_totals(sessions)
        summary = self.stats.summary(top=5, recent=5, today=today)
        try:
            goal = max(0, int(self.goal_minutes() or 0))
        except (TypeError, ValueError):   # meta escrita errada no config.json: fica sem meta
            goal = 0
        since = period_start(today, self.period)
        current = self.stats.current
        return {
            "today": today, "days": days, "summary": summary, "goal": goal,
            "empty": summary.total <= 0,
            "bars": period_bars(days, today, self.period),
            "presets": top_in(sessions, "presets", since),
            "amps": top_in(sessions, "amps", since),
            "achievements": achievements(days, today, goal),
            "week_sessions": sessions_since(sessions, today - timedelta(days=6)),
            "live_start": current.get("start") if current else None,
        }

    def _facts(self, d: dict, t: Translator) -> list[tuple[str | None, str]]:
        s = d["summary"]
        if d["empty"]:
            return [(t("stats_empty_title"), t("stats_empty_body")), (None, t("stats_empty_hint"))]
        if s.streak >= 2:
            streak = (t("fact_streak", n=s.streak),
                      t("fact_streak_record") if s.streak >= s.best_streak else t("fact_streak_sub", best=s.best_streak))
        elif s.streak == 1:
            streak = (t("fact_one_day"), t("fact_one_day_sub"))
        else:
            streak = (t("fact_no_streak"), t("fact_no_streak_best", best=s.best_streak) if s.best_streak >= 2
                      else t("fact_no_streak_sub"))
        n = d["week_sessions"]
        week_sub = t("fact_week_sub", n=n) if n > 1 else t("fact_week_sub_one") if n == 1 else t("fact_week_sub_none")
        return [streak, (format_time(s.week, long=True), week_sub), (f"{int(s.total // 3600)} h" if s.total >= 3600 else format_time(s.total), t("fact_total_sub"))]

    # ---- desenho -----------------------------------------------------------------------------
    def render(self, width: float, scale: float, t: Translator) -> K.Rendered:
        d = self._collect()
        m = K.Painter(1, 1, scale)                      # só para medir texto
        inner = width - 2 * PAD_X
        col = (inner - GAP) / 2

        facts = self._facts(d, t)
        facts_h = sum((K.paragraph_height(m, big, FACT_BIG, FACTS_W) if big else 0)
                      + K.paragraph_height(m, small, FACT, FACTS_W) for big, small in facts) + 14 * (len(facts) - 1)
        chart_h = 2 + 40 + max(CHART_H, facts_h)
        badges = self._badges(d, t)
        badge_cols = len(badges)
        badge_w = (inner - 42 - 10 * (badge_cols - 1)) / badge_cols
        badge_h = max(self._badge_height(m, b, badge_w) for b in badges)
        ach_h = 2 + 36 + 15 * 1.2 + 12 + badge_h
        cal_h = 2 + 36 + 18 + 12 + CAL_TOP + 7 * (CAL_CELL + CAL_GAP) - CAL_GAP + 10 + 14
        presets_h = 2 + 36 + 18 + 12 + self._list_height(m, d["presets"], col)
        amps_h = 2 + 36 + 18 + 12 + self._list_height(m, d["amps"], col)
        recent_n = len(d["summary"].recent)
        recent_h = 2 + 36 + 18 + 12 + (recent_n * REC_H if recent_n else K.paragraph_height(m, t("recent_empty"), EMPTY, col - 42))
        row1 = max(cal_h, presets_h)
        row2 = max(amps_h, recent_h)
        total = PAD_TOP + 36 + GAP + chart_h + GAP + ach_h + GAP + row1 + GAP + row2 + PAD_BOTTOM

        p = K.Painter(width, total, scale)
        regions: list[K.Region] = []
        y = PAD_TOP
        p.text(PAD_X, y + 3, t("stats_heading"), TITLE)
        labels = [t("period_days"), t("period_weeks"), t("period_all")]
        _w, _h, segs = K.segmented(p, width - PAD_X, y, labels, PERIODS.index(self.period), list(PERIODS),
                                   [lambda k=k: self.set_period(k) for k in PERIODS])
        regions += segs
        y += 36 + GAP

        self._chart_panel(p, PAD_X, y, inner, chart_h, d, facts, facts_h, t)
        y += chart_h + GAP

        cx, cy, cw = self._panel(p, PAD_X, y, inner, ach_h, t("ach_title"))
        self._draw_badges(p, cx, cy, cw, badges, badge_w)
        y += ach_h + GAP

        cx, cy, cw = self._panel(p, PAD_X, y, col, row1, t("cal_title"))
        self._calendar(p, cx, cy, d, t)
        cx, cy, cw = self._panel(p, PAD_X + col + GAP, y, col, row1, t("stats_top_presets"))
        self._list(p, cx, cy, cw, d["presets"], t("list_presets_empty") if d["empty"] else t("list_period_empty"))
        y += row1 + GAP

        cx, cy, cw = self._panel(p, PAD_X, y, col, row2, t("stats_top_amps"))
        self._list(p, cx, cy, cw, d["amps"], t("list_amps_empty") if d["empty"] else t("list_period_empty"))
        cx, cy, cw = self._panel(p, PAD_X + col + GAP, y, col, row2, t("stats_recent"))
        self._recent(p, cx, cy, cw, d, t)
        return K.Rendered(p.img, total, regions)

    def _panel(self, p: K.Painter, x: float, y: float, w: float, h: float, title: str) -> tuple[float, float, float]:
        p.rrect(x, y, w, h, 16, K.PANEL, outline=K.PANEL_LINE)
        p.text(x + 21, y + 19, title, H3)
        return x + 21, y + 19 + 15 * 1.2 + 12, w - 42

    # ---- gráfico ----
    def _chart_panel(self, p: K.Painter, x: float, y: float, w: float, h: float, d: dict,
                     facts: list, facts_h: float, t: Translator) -> None:
        chart_x = x + 1 + 22
        chart_w = w - 2 - 44 - FACTS_W - 24
        inner_h = h - 42
        chart_y = y + 21 + (inner_h - CHART_H) / 2
        bars: list[Bar] = d["bars"]
        slot = (chart_w - 30) / len(bars)
        light = None
        if not d["empty"]:
            now = next((i for i, b in enumerate(bars) if b.current), len(bars) - 1)
            lx = chart_x + 30 + now * slot + slot / 2 - x
            light = K.radial_light(p.px(w), p.px(h), p.px(lx), p.px(-30), p.px(110), p.px(250), LIGHT)
        p.rrect(x, y, w, h, 18, K.STAGE, outline=K.RAIL_LINE, light=light)
        self._bars(p, chart_x, chart_y, chart_w, CHART_H, bars, d["goal"], t)
        fx = chart_x + chart_w + 24
        fy = y + 21 + (inner_h - facts_h) / 2
        for big, small in facts:
            if big:
                fy += p.paragraph(fx, fy, big, FACT_BIG, FACTS_W)
            fy += p.paragraph(fx, fy, small, FACT, FACTS_W) + 14

    def _bars(self, p: K.Painter, x0: float, y0: float, w: float, h: float, bars: list[Bar], goal: int,
              t: Translator) -> None:
        pad_l, pad_b, pad_t = 30, 22, 18
        ch = h - pad_b - pad_t
        base = y0 + pad_t + ch
        slot = (w - pad_l) / len(bars)
        bw = min(22, slot * 0.62)
        minutes = [b.seconds / 60 for b in bars]
        daily = self.period == "days"
        floor = 90 if daily else 360 if self.period == "weeks" else 1200
        ticks, top = nice_ticks(max(max(minutes), goal if daily else 0, floor))
        hours = ticks[1] >= 60
        for v in ticks:
            gy = base - v / top * ch
            p.hline(x0 + pad_l, x0 + w, gy, K.GRID)
            p.label(x0 + pad_l - 8, gy, f"{v // 60} h" if hours and v else str(v), AXIS, anchor="r")
        if daily and goal:
            gy = base - goal / top * ch
            p.hline(x0 + pad_l, x0 + w, gy, K.AMBER, width=1.5, dash=(5, 4))
            p.label(x0 + pad_l + 4, gy - 10, t("chart_goal", n=goal), GOAL)
        initials = t("weekday_initials").split(",")
        months = t("months_short").split(",")
        for i, (bar, m) in enumerate(zip(bars, minutes)):
            bx = x0 + pad_l + i * slot + (slot - bw) / 2
            bh = m / top * ch
            if m > 0:
                fill = K.gradient(p.px(bw), max(1, p.px(bh)), K.AMBER, K.ORANGE) if bar.current else K.BAR
                p.top_rounded_bar(bx, base - bh, bw, bh, 6, fill)
            else:
                p.rect(bx, base - 2, bw, 2, K.BAR)
            if daily:
                label = initials[(bar.start.weekday() + 1) % 7]
            elif self.period == "weeks":
                first = next((bar.start + timedelta(days=k) for k in range(7) if (bar.start + timedelta(days=k)).day == 1), None)
                label = months[first.month - 1] if first else ""
            else:
                label = months[bar.start.month - 1]
            if label:
                p.label(bx + bw / 2, y0 + h - 9, label, AXIS_NOW if bar.current else AXIS, anchor="m")
            if bar.current and m > 0:
                p.label(bx + bw / 2, base - bh - 11, str(int(m)) if daily else format_time(bar.seconds), VALUE, anchor="m")

    # ---- conquistas ----
    def _badges(self, d: dict, t: Translator) -> list[tuple[Achievement, str, str]]:
        out = []
        for a in d["achievements"]:
            if a.key.startswith("streak"):
                title = t("ach_streak", n=a.target)
                sub = t("ach_best", n=int(a.value)) if a.value else t("ach_of", n=0, total=a.target)
            elif a.key.startswith("hours"):
                title = t("ach_hours", n=a.target)
                sub = t("ach_hours_of", n=int(a.value), total=a.target)
            else:
                title = t("ach_goal_week")
                sub = t("ach_goal_of", n=int(a.value))
            if a.got:
                sub = t("ach_on", date=t("date_short", d=a.got.day, m=a.got.month))
            out.append((a, title, sub))
        return out

    def _badge_height(self, m: K.Painter, badge: tuple[Achievement, str, str], w: float) -> float:
        a, title, sub = badge
        h = 52 + 7 + K.paragraph_height(m, title, BADGE_TITLE, w) + K.paragraph_height(m, sub, BADGE_SUB, w)
        return h + (0 if a.got else 7 + 4)

    def _draw_badges(self, p: K.Painter, x: float, y: float, w: float, badges: list, col_w: float) -> None:
        for i, (a, title, sub) in enumerate(badges):
            cx = x + i * (col_w + 10) + col_w / 2
            mx = cx - 26
            if a.got:
                p.shadow(mx, y, 52, 52, 15, (255, 106, 61, 204), dy=10, blur=22, spread=-10)
                p.rrect(mx, y, 52, 52, 15, K.gradient(p.px(52), p.px(52), K.AMBER, K.ORANGE))
                p.icon(BADGE_ICONS[a.key], cx - 12, y + 14, 24, K.BADGE_ICON)
            else:
                p.rrect(mx, y, 52, 52, 15, K.BADGE_OFF, outline=K.FIELD_LINE)
                p.icon(BADGE_ICONS[a.key], cx - 12, y + 14, 24, K.DIM)
            ty = y + 52 + 7
            for line in p.wrap(title, BADGE_TITLE, col_w):
                p.text(cx, ty, line, BADGE_TITLE, anchor="m")
                ty += BADGE_TITLE.size * BADGE_TITLE.line
            for line in p.wrap(sub, BADGE_SUB, col_w):
                p.text(cx, ty, line, BADGE_SUB, anchor="m")
                ty += BADGE_SUB.size * BADGE_SUB.line
            if not a.got:
                ty += 7
                p.rrect(cx - col_w / 2, ty, col_w, 4, 2, K.TRACK)
                if a.progress > 0:
                    p.rrect(cx - col_w / 2, ty, max(4, col_w * a.progress), 4, 2, K.ICON_OFF)

    # ---- calendário ----
    def _calendar(self, p: K.Painter, x: float, y: float, d: dict, t: Translator) -> None:
        today: date = d["today"]
        first = week_start(today) - timedelta(weeks=15)
        step = CAL_CELL + CAL_GAP
        months = t("months_short").split(",")
        initials = t("weekday_initials").split(",")
        last_col = -9
        for i in range(112):
            day = first + timedelta(days=i)
            col = i // 7
            if day > today:
                break
            if day.day == 1 and col - last_col >= 2:
                p.text(x + CAL_LEFT + col * step, y + 1, months[day.month - 1], CAL)
                last_col = col
        for r in (1, 3, 5):
            p.label(x, y + CAL_TOP + r * step + CAL_CELL / 2, initials[r], CAL)
        days = d["days"]
        for i in range(112):
            day = first + timedelta(days=i)
            if day > today:
                break
            cx = x + CAL_LEFT + (i // 7) * step
            cy = y + CAL_TOP + (i % 7) * step
            color = K.CAL_RAMP[0 if d["empty"] else level(days.get(day, 0.0))]
            p.rrect(cx, cy, CAL_CELL, CAL_CELL, 3, color, outline=K.GLOW if day == today else None)
        ly = y + CAL_TOP + 7 * step - CAL_GAP + 10 + 7
        lx = x + p.label(x, ly, t("legend_less"), LEGEND) + 4
        for color in K.CAL_RAMP:
            p.rrect(lx, ly - 5.5, 11, 11, 3, color)
            lx += 15
        p.label(lx, ly, t("legend_more"), LEGEND)

    # ---- listas ----
    def _list_height(self, m: K.Painter, items: list, w: float) -> float:
        return len(items) * ROW_H if items else K.paragraph_height(m, "x", EMPTY, w)

    def _list(self, p: K.Painter, x: float, y: float, w: float, items: list[tuple[str, float]], empty: str) -> None:
        if not items:
            p.paragraph(x, y, empty, EMPTY, w)
            return
        name_w = w - 92 - 56 - 20
        top = items[0][1] or 1
        for i, (name, secs) in enumerate(items):
            ty = y + i * ROW_H + 6
            p.text(x, ty, name, ROW, max_w=name_w)
            bx, by = x + name_w + 10, ty + (13 * 1.4 - 6) / 2
            p.rrect(bx, by, 92, 6, 3, K.TRACK)
            fill_w = max(6, 92 * secs / top)
            fill = K.gradient(p.px(fill_w), p.px(6), K.AMBER, K.ORANGE, horizontal=True) if i == 0 else K.DIM
            p.rrect(bx, by, fill_w, 6, 3, fill)
            p.text(x + w, ty, format_time(secs), ROW_SOFT, anchor="r")

    def _recent(self, p: K.Painter, x: float, y: float, w: float, d: dict, t: Translator) -> None:
        recent = d["summary"].recent
        if not recent:
            p.paragraph(x, y, t("recent_empty"), EMPTY, w)
            return
        weekdays = t("weekdays_short").split(",")
        for i, s in enumerate(recent):
            top = y + i * REC_H
            if i:
                p.hline(x, x + w, top, K.PANEL_LINE)
            when = datetime.fromtimestamp(s.get("start", 0))
            if when.date() == d["today"]:
                label = t("today_at", time=when.strftime("%H:%M"))
            else:
                label = f"{weekdays[(when.weekday() + 1) % 7]} {t('date_short', d=when.day, m=when.month)}, {when:%H:%M}"
            name = (s.get("last_preset")
                    or (t("plugin_host", host=s["host"]) if s.get("mode") == "plugin" and s.get("host") else s.get("host"))
                    or "Guitar Rig 7")
            live = d["live_start"] is not None and s.get("start") == d["live_start"]
            dur = t("stats_live") if live else format_time(s.get("seconds", 0))
            dur_style = LIVE if live else ROW
            dur_w = p.text(x + w, top + 7, dur, dur_style, anchor="r")
            p.text(x, top + 7, label, ROW_MUTED, max_w=130)
            p.text(x + 130 + 12, top + 7, name, ROW, max_w=w - 130 - 24 - dur_w)
