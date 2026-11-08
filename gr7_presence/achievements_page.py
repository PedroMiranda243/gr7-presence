"""Página Conquistas da janela principal, desenhada pelo Pillow como nos exemplos aprovados (Palco).

De cima para baixo: o palco com o nível de músico, os pontos e a conquista mais recente; um painel por
grupo do catálogo, com uma medalha por conquista; e a linha do tempo. Numa janela larga (tela cheia),
cabem dois grupos por linha e a linha do tempo ocupa o espaço que sobra no fim.

As medalhas também aparecem na linha das Estatísticas (`badge_height` e `draw_badge`).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

from . import ui_kit as K
from .achievement_view import level_name, mark_title, medal_colors, number, short_date, thousands, unit
from .achievements import (BY_KEY, CATALOG, GROUPS, AchievementTracker, Result, Unlock, musician_level,
                           total_marks, total_points, unlocked_marks, unlocks)
from .dashboard_page import LIGHT, META
from .i18n import Translator

PAD_X, PAD_TOP, PAD_BOTTOM, GAP = 24, 20, 24, 14
CELL_GAP = 10              # entre as medalhas de um painel
CELL_MIN = 150             # uma medalha precisa disso para caber; abaixo, a linha fica com 5
MEDAL = 52
STAGE_H = 176
TIMELINE_ROWS = 8          # na janela padrão, a linha do tempo mostra as 8 mais recentes
REC_H = 34
TIMELINE_MIN_W = 300       # sobra mais estreita que isso numa linha: a linha do tempo vai para baixo
FILTERS = ("all", "got", "missing")

TITLE = K.Style(30, 800, K.TEXT, display=True, width=125, line=1.0)
H3 = K.Style(15, 700, K.TEXT, display=True, width=112, line=1.2)
LEVEL_BIG = K.Style(44, 800, K.GLOW, display=True, width=125, line=1.0)
LABEL = K.Style(11.5, 600, K.MUTED, line=1.2)
MARKS = K.Style(13, 400, K.MUTED, line=1.3)
RECENT_TITLE = K.Style(17, 700, K.TEXT, display=True, width=112, line=1.2)
RECENT_SUB = K.Style(13, 400, K.TEXT_SOFT, line=1.3)
POINTS = K.Style(13, 600, K.AMBER, line=1.3)
BADGE_TITLE = K.Style(12.5, 600, K.TEXT, line=1.3)
BADGE_SUB = K.Style(12, 400, K.TEXT_SOFT, line=1.3)
ROW = K.Style(13, 400, K.TEXT, line=1.4)
ROW_SOFT = K.Style(13, 400, K.TEXT_SOFT, line=1.4)
ROW_MUTED = K.Style(13, 400, K.MUTED, line=1.4)
EMPTY = K.Style(13.5, 400, K.MUTED, line=1.5)


# ---- o que cada medalha mostra ----------------------------------------------------------------------
@dataclass(frozen=True)
class Badge:
    """Uma medalha pronta para desenhar: ícone, cores (None = apagada), textos, pontinhos e progresso."""
    key: str
    icon: str
    colors: tuple[str, str, str] | None
    title: str
    sub: str
    pips: int                    # quantos níveis a família tem (0 nas únicas)
    level: int
    progress: float | None       # a barra fina até o próximo nível (None: sem barra)


def badge(r: Result, t: Translator, today: date, first: date | None = None) -> Badge:
    """A medalha de uma conquista. `first`: o dia da primeira sessão (para "1 ano tocando")."""
    d = r.definition
    if d.secret and not r.level:
        return Badge(r.key, "question", None, t("ach_secret"), t("ach_secret_sub"), 0, 0, None)
    title = t(f"ach_{r.key}")
    if d.levels:
        total = len(d.levels)
        if r.maxed:
            sub = t("ach_recent_sub", level=t(f"ach_level_{r.level}"), date=short_date(r.got, t))
            progress = None
        elif d.new_data and r.value <= 0:
            sub, progress = t("ach_new_data"), None
        else:
            prog = t("ach_progress", n=number(r.value, t), total=number(r.next_target, t),
                     unit=unit(r.key, r.next_target, t))
            sub = t("ach_level_progress", level=t(f"ach_level_{r.level}"), progress=prog) if r.level else prog
            progress = r.progress
        return Badge(r.key, d.icon, medal_colors(r.key, r.level), title, sub, total, r.level, progress)
    if r.level:
        sub = t("ach_on", date=short_date(r.got, t))
    elif r.key == "one_year" and first:
        left = (first + timedelta(days=365) - today).days
        sub = t("ach_one_year_left_one") if left == 1 else t("ach_one_year_left", n=left) if left > 1 \
            else t("ach_one_year_desc")
    else:
        sub = t(f"ach_{r.key}_desc")
        if d.new_data:
            sub = t("ach_since_new", desc=sub)
    return Badge(r.key, d.icon, medal_colors(r.key, r.level), title, sub, 0, r.level, None)


def badge_height(m: K.Painter, b: Badge, w: float) -> float:
    """A altura de uma medalha com os textos. A linha dos pontinhos existe também nas únicas, vazia,
    para os títulos de um painel ficarem alinhados."""
    h = MEDAL + 7 + 5 + 8
    h += K.paragraph_height(m, b.title, BADGE_TITLE, w) + K.paragraph_height(m, b.sub, BADGE_SUB, w)
    return h + (11 if b.progress is not None else 0)


def draw_badge(p: K.Painter, cx: float, y: float, w: float, b: Badge) -> None:
    """Uma medalha centrada em `cx`, com `w` de largura para os textos."""
    K.medal(p, cx, y, MEDAL, b.icon, b.colors)
    ty = y + MEDAL + 7
    if b.pips:
        K.pips(p, cx, ty + 2.5, b.pips, b.level)
    ty += 5 + 8
    for line in p.wrap(b.title, BADGE_TITLE, w):
        p.text(cx, ty, line, BADGE_TITLE, anchor="m")
        ty += BADGE_TITLE.size * BADGE_TITLE.line
    for line in p.wrap(b.sub, BADGE_SUB, w):
        p.text(cx, ty, line, BADGE_SUB, anchor="m")
        ty += BADGE_SUB.size * BADGE_SUB.line
    if b.progress is not None:
        ty += 7
        p.rrect(cx - w / 2, ty, w, 4, 2, K.TRACK)
        if b.progress > 0:   # na cor do próximo nível
            p.rrect(cx - w / 2, ty, max(4, w * b.progress), 4, 2, K.MEDAL_LEVELS[min(b.level, 4)][1])


def first_session(results: list[Result]) -> date | None:
    return next((r.got for r in results if r.key == "first"), None)


def highlights(results: list[Result], n: int = 5, recent: int = 3) -> list[Result]:
    """As medalhas da linha das Estatísticas: as `recent` destravadas mais recentes e, depois, as mais
    perto do próximo nível (as secretas escondidas e as que ainda não começaram a contar ficam de fora)."""
    by_key = {r.key: r for r in results}
    out: list[Result] = []
    for u in unlocks(results):
        if len(out) >= recent:
            break
        if by_key[u.key] not in out:
            out.append(by_key[u.key])
    order = {d.key: i for i, d in enumerate(CATALOG)}
    rest = [r for r in results if r not in out and not r.maxed and not (r.definition.secret and not r.level)
            and not (r.definition.new_data and r.value <= 0)]
    rest.sort(key=lambda r: (-(r.progress if r.definition.levels else 0.0), order[r.key]))
    return (out + rest)[:n]


# ---- a página ---------------------------------------------------------------------------------------
def columns(inner: float) -> int:
    """5 medalhas por linha na janela padrão; numa janela larga, 10 (dois grupos de 5 lado a lado)."""
    return 5 * max(1, int((inner + GAP) // (5 * CELL_MIN + 42 + GAP)))


def pack(groups: list[tuple[str, list[Badge]]], cols: int) -> list[tuple[list[tuple[str, list[Badge]]], int]]:
    """Os grupos em linhas de até `cols` medalhas, na ordem, sem quebrar um grupo."""
    rows: list = []
    row: list = []
    used = 0
    for g in groups:
        n = len(g[1])
        if row and used + n > cols:
            rows.append((row, used))
            row, used = [], 0
        row.append(g)
        used += n
    if row:
        rows.append((row, used))
    return rows


class AchievementsPage:
    key = "achievements"
    icon = "trophy"
    label_key = "nav_achievements"

    def __init__(self, tracker: AchievementTracker, today: Callable[[], date] = date.today):
        self.tracker = tracker
        self.today = today
        self.filter = "all"
        self.on_change: Callable[[], None] = lambda: None

    def set_filter(self, key: str) -> None:
        if key != self.filter:
            self.filter = key
            self.on_change()

    def on_show(self) -> None:
        """A janela chama quando a página aparece: as conquistas novas passam a ser vistas."""
        self.tracker.mark_seen()

    def has_news(self) -> bool:
        """O ponto laranja na barra lateral: há conquista que a pessoa ainda não viu aqui."""
        return bool(self.tracker.unseen())

    # ---- dados ----
    def _groups(self, results: list[Result], t: Translator, today: date) -> list[tuple[str, list[Badge]]]:
        first = first_session(results)
        keep = {"all": lambda r: True, "got": lambda r: r.level > 0, "missing": lambda r: not r.maxed}[self.filter]
        out = []
        for group in GROUPS:
            items = [badge(r, t, today, first) for r in results if r.definition.group == group and keep(r)]
            if items:
                out.append((t(f"ach_group_{group}"), items))
        return out

    # ---- desenho ----
    def render(self, width: float, scale: float, t: Translator) -> K.Rendered:
        today = self.today()
        # A janela só desenha a página que está aberta: o que sair enquanto ela está na tela já foi visto.
        self.tracker.mark_seen()
        results = self.tracker.current(today)
        timeline = unlocks(results)
        inner = width - 2 * PAD_X
        cols = columns(inner)
        rows = pack(self._groups(results, t, today), cols)
        m = K.Painter(1, 1, scale)

        # as alturas antes de desenhar (a imagem precisa nascer com o tamanho certo)
        plan = []
        for row, used in rows:
            k = len(row)
            cell_w = (inner - k * 42 - (k - 1) * GAP - (cols - k) * CELL_GAP) / cols
            row_h = 2 + 36 + 15 * 1.2 + 12 + max(badge_height(m, b, cell_w) for _title, items in row for b in items)
            plan.append((row, used, cell_w, row_h))
        side = None   # (índice da linha, x, largura) da linha do tempo ao lado do último grupo
        if plan and cols > 5:
            row, used, cell_w, row_h = plan[-1]
            right = PAD_X + sum(len(items) * cell_w + (len(items) - 1) * CELL_GAP + 42 + GAP for _t, items in row)
            if used < cols and PAD_X + inner - right >= TIMELINE_MIN_W:
                side = (len(plan) - 1, right, PAD_X + inner - right)
        n_lines = min(TIMELINE_ROWS, len(timeline))
        timeline_h = 2 + 36 + 18 + 12 + (n_lines * REC_H if n_lines
                                          else K.paragraph_height(m, t("ach_timeline_empty"), EMPTY, inner - 42))
        empty_h = 2 + 36 + 18 + 12 + K.paragraph_height(m, t("ach_filter_empty"), EMPTY, inner - 42)
        total = PAD_TOP + 36 + GAP + STAGE_H + GAP
        total += sum(row_h + GAP for *_r, row_h in plan) if plan else empty_h + GAP
        if side is None:
            total += timeline_h + GAP
        total += PAD_BOTTOM - GAP

        p = K.Painter(width, total, scale)
        regions: list[K.Region] = []
        y = PAD_TOP
        p.text(PAD_X, y + 3, t("ach_title"), TITLE)
        labels = [t("ach_filter_all"), t("ach_filter_got"), t("ach_filter_missing")]
        _w, _h, segs = K.segmented(p, width - PAD_X, y, labels, FILTERS.index(self.filter), list(FILTERS),
                                   [lambda k=k: self.set_filter(k) for k in FILTERS])
        regions += segs
        y += 36 + GAP

        self._stage(p, PAD_X, y, inner, results, timeline, t)
        y += STAGE_H + GAP

        if not plan:
            cx, cy, cw = self._panel(p, PAD_X, y, inner, empty_h, t("ach_title"))
            p.paragraph(cx, cy, t("ach_filter_empty"), EMPTY, cw)
            y += empty_h + GAP
        for i, (row, used, cell_w, row_h) in enumerate(plan):
            x = PAD_X
            for title, items in row:
                n = len(items)
                pw = n * cell_w + (n - 1) * CELL_GAP + 42
                cx, cy, _cw = self._panel(p, x, y, pw, row_h, title)
                for j, b in enumerate(items):
                    draw_badge(p, cx + j * (cell_w + CELL_GAP) + cell_w / 2, cy, cell_w, b)
                x += pw + GAP
            if side and side[0] == i:
                cx, cy, cw = self._panel(p, side[1], y, side[2], row_h, t("ach_timeline"))
                self._timeline(p, cx, cy, cw, timeline, int((row_h - 70) // REC_H), t)
            y += row_h + GAP
        if side is None:
            cx, cy, cw = self._panel(p, PAD_X, y, inner, timeline_h, t("ach_timeline"))
            self._timeline(p, cx, cy, cw, timeline, n_lines, t)
        return K.Rendered(p.img, total, regions)

    def _panel(self, p: K.Painter, x: float, y: float, w: float, h: float, title: str) -> tuple[float, float, float]:
        p.rrect(x, y, w, h, 16, K.PANEL, outline=K.PANEL_LINE)
        p.text(x + 21, y + 19, title, H3)
        return x + 21, y + 19 + 15 * 1.2 + 12, w - 42

    def _stage(self, p: K.Painter, x: float, y: float, w: float, results: list[Result], timeline: list[Unlock],
               t: Translator) -> None:
        light = K.radial_light(p.px(w), p.px(STAGE_H), p.px(w * 0.2), p.px(-STAGE_H * 0.25),
                               p.px(w * 0.55), p.px(STAGE_H * 1.3), LIGHT)
        p.rrect(x, y, w, STAGE_H, 18, K.STAGE, light=light)
        points = total_points(results)
        level, into, missing = musician_level(points)
        sx, sy = x + 28, y + 26
        p.text(sx, sy, t("ach_level_label"), LABEL)
        p.text(sx, sy + 18, t("ach_level", n=level), LEVEL_BIG)
        pts = thousands(points, t)
        p.text(sx, sy + 70, t("ach_points_line", points=pts, missing=missing, next=level + 1), META)
        bar_w = min(380, w * 0.45)
        p.rrect(sx, sy + 100, bar_w, 10, 5, K.TRACK)
        fill = bar_w * into / (into + missing)
        if fill >= 1:
            p.rrect(sx, sy + 100, max(10, fill), 10, 5,
                    K.gradient(p.px(max(10, fill)), p.px(10), K.AMBER, K.ORANGE, horizontal=True))
        secrets = [r for r in results if r.definition.secret]
        p.text(sx, sy + 120, t("ach_marks_line", n=unlocked_marks(results), total=total_marks(results),
                               s=sum(r.level for r in secrets), s_total=len(secrets)), MARKS)

        # a mais recente
        rw = 250
        rx = x + w - 28 - rw
        p.rrect(rx, y + 22, rw, STAGE_H - 44, 14, K.PANEL, outline=K.PANEL_LINE)
        p.text(rx + 18, y + 36, t("ach_recent_label"), LABEL)
        if not timeline:
            K.medal(p, rx + 18 + 28, y + 60, 56, "trophy", None)
            tx = rx + 18 + 56 + 16
            p.text(tx, y + 66, t("ach_recent_none"), RECENT_TITLE, max_w=rw - (tx - rx) - 14)
            p.paragraph(tx, y + 90, t("ach_recent_none_sub"), RECENT_SUB, rw - (tx - rx) - 14)
            return
        u = timeline[0]
        d = BY_KEY[u.key]
        K.medal(p, rx + 18 + 28, y + 60, 56, d.icon, medal_colors(u.key, u.level))
        tx = rx + 18 + 56 + 16
        p.text(tx, y + 62, t(f"ach_{u.key}"), RECENT_TITLE, max_w=rw - (tx - rx) - 14)
        p.text(tx, y + 86, t("ach_recent_sub", level=level_name(u.key, u.level, t), date=short_date(u.got, t)),
               RECENT_SUB, max_w=rw - (tx - rx) - 14)
        p.text(tx, y + 106, t("ach_points_plus", n=u.points), POINTS)

    def _timeline(self, p: K.Painter, x: float, y: float, w: float, timeline: list[Unlock], n: int,
                  t: Translator) -> None:
        if not timeline:
            p.paragraph(x, y, t("ach_timeline_empty"), EMPTY, w)
            return
        for i, u in enumerate(timeline[:max(0, n)]):
            ry = y + i * REC_H
            if i:
                p.rect(x, ry - 1, w, 1, K.PANEL_LINE)
            p.text(x, ry + 8, t("date_full", d=u.got.day, m=u.got.month, y=u.got.year), ROW_MUTED)
            K.medal(p, x + 104, ry + 5, 22, BY_KEY[u.key].icon, medal_colors(u.key, u.level))
            p.text(x + 124, ry + 8, mark_title(u, t), ROW, max_w=w - 124 - 50)
            p.text(x + w, ry + 8, f"+{u.points}", ROW_SOFT, anchor="r")
