"""Página Painel da janela principal: o que está no perfil agora, como no exemplo aprovado (Palco).

No palco, com a luz em cima, o preset que está tocando, a cadeia do rack e o cartão que o Discord está
mostrando, com o rodízio. Embaixo, a meta do dia e as conexões (Discord, Guitar Rig, leitura da tela).
Com o Guitar Rig fechado, a luz apaga e a página diz o que acontece quando ele abrir.

Numa janela maior que a padrão (tela cheia), o Painel é o desenho da janela padrão ampliado por igual
até ocupar a largura ou a altura, centralizado (opção B, escolhida pelo dono do projeto). Se ganhar
painéis, em tela cheia eles ficam mais lado a lado para tudo caber numa tela só (`_fit`); na janela
padrão, a página rola como as outras.
"""
from __future__ import annotations

import dataclasses
import math
import time
from datetime import date, datetime, timedelta
from typing import Callable

from . import ui_kit as K
from .i18n import Translator, format_time

PAD_X, PAD_TOP, PAD_BOTTOM, GAP = 24, 20, 20, 14
CARD_W = 290
BASE_W = 960 - 78        # a página na janela padrão (o SIZE da main_window menos o trilho)
PANEL_MIN_W = 400        # a menor largura de um painel de baixo: na janela padrão cabem dois lado a lado
NAME = K.Style(46, 800, K.GLOW, display=True, width=125, line=0.98)
NAME_MD = K.Style(38, 800, K.GLOW, display=True, width=125, line=0.98)
META = K.Style(14, 400, K.TEXT_LEAD, line=1.5)
META_MUTED = K.Style(14, 400, K.MUTED, line=1.5)
PILL = K.Style(12.5, 500, K.PILL_TEXT, line=1.2)
PILL_AMP = K.Style(12.5, 600, K.WHITE, line=1.2)
LIVE = K.Style(13, 400, K.TEXT_LEAD, line=1.3)
H3 = K.Style(15, 700, K.TEXT, display=True, width=112, line=1.2)
BIG = K.Style(34, 800, K.TEXT, display=True, width=118, line=1.0)
BIG_SUB = K.Style(14, 400, K.MUTED, line=1.0)
NOTE = K.Style(13, 400, K.MUTED, line=1.45)
CONN = K.Style(13.5, 400, K.TEXT, line=1.3)
CONN_R = K.Style(13, 400, K.MUTED, line=1.3)
CONN_HINT = K.Style(13, 400, K.MUTED, line=1.4)   # quebra onde o 12,5 do exemplo quebra
ROTATION = K.Style(12, 400, K.MUTED, line=1.3)
EMPTY = K.Style(13, 400, K.MUTED, line=1.45)
BUTTON = K.Style(13, 600, K.TEXT, line=1.3)

LIGHT = [(0.0, (255, 183, 77, 0.36)), (0.40, (255, 106, 61, 0.15)), (0.72, (17, 19, 26, 0.0)), (1.0, (17, 19, 26, 0.0))]
LIGHT_OFF = [(0.0, (160, 170, 200, 0.12)), (0.70, (17, 19, 26, 0.0)), (1.0, (17, 19, 26, 0.0))]
VERBS = {0: "playing", 2: "listening", 3: "watching", 5: "competing"}
PILL_H = 6 + 12.5 * 1.2 + 6 + 2


@dataclasses.dataclass
class BottomPanel:
    """Um painel embaixo do palco: o título, a altura do conteúdo numa largura e o desenho do conteúdo."""
    title: str
    height: Callable[[K.Painter, float], float]               # (medidor, largura do conteúdo) -> altura
    draw: Callable[[K.Painter, float, float, float], None]    # (pintor, x, y, largura do conteúdo)


class DashboardPage:
    key = "dashboard"
    icon = "dash"
    label_key = "nav_dashboard"
    refresh_ms = 1000    # o tempo do cartão e o "troca em" contam de segundo em segundo

    def __init__(self, app, today: Callable[[], date] = date.today, now: Callable[[], float] = time.time):
        self.app = app
        self.today = today
        self.now = now
        self.on_change: Callable[[], None] = lambda: None
        self.host = None
        self.view_height = 0.0           # a janela informa a altura visível; sem ela, nada de ampliar
        self._place = (1.0, 0.0)         # ampliação e deslocamento do último desenho, para a lista do Pausar

    # ---- ações ---------------------------------------------------------------------------------
    def _pause(self, how: str) -> None:
        self.app.set_paused(True, 3600 if how == "hour" else None)
        self.on_change()

    def _resume(self) -> None:
        self.app.set_paused(False)
        self.on_change()

    # ---- desenho -------------------------------------------------------------------------------
    def render(self, width: float, scale: float, t: Translator) -> K.Rendered:
        state = self.app.last_state
        layout_w, zoom = self._fit(width, scale, t, state)
        if zoom == 1.0:
            self._place = (1.0, 0.0)
            return self._render(width, scale, t, state)
        # O desenho numa largura menor, em pixels de tela maiores, no meio da largura.
        dx = (width - layout_w * zoom) / 2
        self._place = (zoom, dx)
        inner = self._render(layout_w, scale * zoom, t, state)
        p = K.Painter(width, inner.height * zoom, scale)
        p.img.paste(inner.image, (p.px(dx), 0))
        regions = [dataclasses.replace(r, x0=dx + r.x0 * zoom, y0=r.y0 * zoom, x1=dx + r.x1 * zoom, y1=r.y1 * zoom,
                                       radius=r.radius * zoom) for r in inner.regions]
        return K.Rendered(p.img, inner.height * zoom, regions)

    def _fit(self, width: float, scale: float, t: Translator, state) -> tuple[float, float]:
        """Em tela cheia: em que largura desenhar e quanto ampliar, até ocupar a largura ou a altura visível.

        Experimenta a largura da janela padrão e as que põem mais painéis de baixo lado a lado, e fica com
        a que deixa tudo maior sem passar da altura. Com os dois painéis de hoje, é sempre a da janela
        padrão. Se o Painel ganhar painéis, eles vão para colunas a mais e tudo continua numa tela só. As
        letras nunca ficam menores que na janela padrão: se nem assim cabe, é o desenho de sempre, na
        largura toda, e a página rola. Na janela padrão, numa mais estreita ou numa mais baixa que o
        conteúdo, a ampliação é 1."""
        view_h = self.view_height or 0
        if width < BASE_W * 1.01 or not view_h:
            return width, 1.0
        best_w, best = width, 1.0
        for cols in range(2, max(2, len(self._panels(t, state))) + 1):
            layout_w = max(BASE_W, cols * (PANEL_MIN_W + GAP) - GAP + 2 * PAD_X)
            if layout_w * 1.01 > width:
                break
            zoom = min(width / layout_w, view_h / self._layout(layout_w, scale, t, state)["total"])
            if zoom >= 1.01:
                # O texto mede um tico diferente em outra escala: confere para não passar da altura e rolar.
                zoom = min(zoom, view_h / self._layout(layout_w, scale * zoom, t, state)["total"])
                zoom = math.floor(zoom * 100) / 100
            if zoom > best:
                best_w, best = layout_w, zoom
        return (best_w, best) if best >= 1.01 else (width, 1.0)

    def _layout(self, width: float, scale: float, t: Translator, state) -> dict:
        """As medidas do Painel numa largura, sem desenhar."""
        m = K.Painter(1, 1, scale)
        inner = width - 2 * PAD_X
        left_w = inner - 56 - CARD_W - 26
        left = self._left(t, state)
        stage_h = 28 + max(self._left_height(m, left, left_w), self._right_height(m, t, state)) + 24
        panels = self._panels(t, state)
        # Dois por linha na janela padrão (e na mínima); numa largura maior, cabem mais lado a lado.
        cols = max(1, min(len(panels), max(2, int((inner + GAP) // (PANEL_MIN_W + GAP)))))
        col = (inner - GAP * (cols - 1)) / cols
        rows = [panels[i:i + cols] for i in range(0, len(panels), cols)]
        row_hs = [max(2 + 36 + 18 + 12 + panel.height(m, col - 42) for panel in row) for row in rows]
        return {"inner": inner, "left_w": left_w, "left": left, "stage_h": stage_h, "col": col, "cols": cols,
                "rows": rows, "row_hs": row_hs,
                "total": PAD_TOP + stage_h + sum(GAP + h for h in row_hs) + PAD_BOTTOM}

    def _panels(self, t: Translator, state) -> list[BottomPanel]:
        """Os painéis embaixo do palco, na ordem. Painel novo entra nesta lista: na janela padrão eles ficam
        de dois em dois, e a página rola se precisar; em tela cheia, o `_fit` põe mais lado a lado."""
        goal_note = self._goal_note(t, state)
        conns = self._connections(t, state)
        return [
            BottomPanel(t("dash_goal_title"),
                        lambda m, w: 34 + 12 + 10 + 10 + K.paragraph_height(m, goal_note, NOTE, w),
                        lambda p, x, y, w: self._draw_goal(p, x, y, w, t, goal_note)),
            BottomPanel(t("conn_title"),
                        lambda m, w: self._conn_height(m, conns, w),
                        lambda p, x, y, w: self._draw_connections(p, x, y, w, conns)),
        ]

    def _render(self, width: float, scale: float, t: Translator, state) -> K.Rendered:
        lay = self._layout(width, scale, t, state)
        inner, left_w, left, stage_h, col = lay["inner"], lay["left_w"], lay["left"], lay["stage_h"], lay["col"]
        total = lay["total"]

        p = K.Painter(width, total, scale)
        regions: list[K.Region] = []
        y = PAD_TOP
        light = K.radial_light(p.px(inner), p.px(stage_h), p.px(inner * 0.26), p.px(-stage_h * 0.22),
                               p.px(inner * 0.58), p.px(stage_h * 1.25), LIGHT if state else LIGHT_OFF)
        p.rrect(PAD_X, y, inner, stage_h, 18, K.STAGE, light=light)
        self._draw_left(p, PAD_X + 28, y + 28, left_w, left, regions, t, state)
        self._draw_right(p, PAD_X + inner - 28 - CARD_W, y + 28, t, state)
        y += stage_h

        for row, row_h in zip(lay["rows"], lay["row_hs"]):
            y += GAP
            for i, panel in enumerate(row):
                cx, cy, cw = self._panel(p, PAD_X + i * (col + GAP), y, col, row_h, panel.title)
                panel.draw(p, cx, cy, cw)
            y += row_h
        return K.Rendered(p.img, total, regions)

    def _panel(self, p: K.Painter, x: float, y: float, w: float, h: float, title: str) -> tuple[float, float, float]:
        p.rrect(x, y, w, h, 16, K.PANEL, outline=K.PANEL_LINE)
        p.text(x + 21, y + 19, title, H3)
        return x + 21, y + 19 + 18 + 12, w - 42

    # ---- o palco, à esquerda ----
    def _left(self, t: Translator, state) -> dict:
        if not state:
            return {"title": t("dash_waiting_title"), "style": NAME_MD, "meta": t("dash_waiting_body"),
                    "extra": self._last_session(t), "pills": [], "live": None}
        preset, target, _tracks, rack_state = state
        pills: list[tuple[str, bool]] = []
        if target.kind == "plugin":
            title, meta = t("dash_in_daw", host=target.host or "DAW"), t("dash_in_daw_meta")
        elif rack_state:
            key = "dash_rack_empty" if rack_state == "empty" else "dash_scratch"
            title, meta = t(key), t(f"{key}_meta")
        elif preset and preset.name:
            title = preset.name
            origin = (t("factory_by", author=preset.author) if preset.is_factory and preset.author else
                      t("user_preset_by", author=preset.author) if preset.author and preset.is_factory is False else
                      t("user_preset"))
            meta = " · ".join([origin] + ([", ".join(preset.tags[:3])] if preset.tags else []))
            pills = [(c, c == preset.amp) for c in preset.chain]
        else:
            title, meta = "Guitar Rig 7", t("dash_reading")
        return {"title": title, "style": NAME, "meta": meta, "extra": None, "pills": pills, "live": target}

    def _last_session(self, t: Translator) -> str | None:
        recent = self.app.stats.summary(top=1, recent=1).recent
        if not recent:
            return None
        s = recent[0]
        when = datetime.fromtimestamp(s.get("start", 0))
        today = self.today()
        if when.date() == today:
            day = t("today_word")
        elif when.date() == today - timedelta(days=1):
            day = t("yesterday_word")
        elif when.date() > today - timedelta(days=7):
            day = t("weekdays_long").split(",")[(when.weekday() + 1) % 7]
        else:
            day = t("date_short", d=when.day, m=when.month)
        what = s.get("last_preset") or s.get("host") or "Guitar Rig 7"
        return t("dash_last_session", when=f"{day}, {when:%H:%M}", dur=format_time(s.get("seconds", 0)), what=what)

    def _pill_rows(self, m: K.Painter, pills: list[tuple[str, bool]], w: float) -> list[list[tuple[str, bool, float]]]:
        rows: list[list[tuple[str, bool, float]]] = [[]]
        x = 0.0
        for label, amp in pills:
            pw = m.measure(label, PILL_AMP if amp else PILL) + 22 + 2
            if rows[-1] and x + pw > w:
                rows.append([])
                x = 0.0
            rows[-1].append((label, amp, pw))
            x += pw + 6
        return [r for r in rows if r]

    def _left_height(self, m: K.Painter, left: dict, w: float) -> float:
        style = left["style"]
        h = 6 + len(m.balanced(left["title"], style, w)) * style.size * style.line + 12
        h += K.paragraph_height(m, left["meta"], META, w)
        if left["extra"]:
            h += 14 + K.paragraph_height(m, left["extra"], META_MUTED, w)
        rows = self._pill_rows(m, left["pills"], w)
        if rows:
            h += 18 + len(rows) * PILL_H + (len(rows) - 1) * 6
        if left["live"]:
            h += 22 + 34
        return h

    def _draw_left(self, p: K.Painter, x: float, y: float, w: float, left: dict, regions: list,
                   t: Translator, state) -> None:
        style = left["style"]
        y += 6
        for line in p.balanced(left["title"], style, w):
            p.text(x, y, line, style)
            y += style.size * style.line
        y += 12
        y += p.paragraph(x, y, left["meta"], META, w)
        if left["extra"]:
            y += 14 + p.paragraph(x, y + 14, left["extra"], META_MUTED, w)
        rows = self._pill_rows(p, left["pills"], w)
        if rows:
            y += 18
            for row in rows:
                px_ = x
                for label, amp, pw in row:
                    if amp:
                        p.rrect(px_, y, pw, PILL_H, PILL_H / 2, K.RED)
                    else:
                        p.rrect(px_, y, pw, PILL_H, PILL_H / 2, K.PILL, outline=K.PILL_LINE)
                    p.text(px_ + 12, y + 7, label, PILL_AMP if amp else PILL)
                    px_ += pw + 6
                y += PILL_H + 6
            y -= 6
        if left["live"]:
            y += 22
            self._draw_live(p, x, y, w, regions, t, left["live"])

    def _draw_live(self, p: K.Painter, x: float, y: float, w: float, regions: list, t: Translator, target) -> None:
        now = self.now()
        app = self.app
        if app.paused:
            dot = K.AMBER
            text = (t("dash_paused_until", time=datetime.fromtimestamp(app.pause_until).strftime("%H:%M"))
                    if app.pause_until else t("dash_paused"))
        elif not app.discord_connected:
            dot, text = K.ORANGE, t("dash_discord_off")
        elif app.showing:
            dot, text = K.GREEN, t("dash_live", t=format_time(max(0, now - target.started_at)))
        else:
            dot, text = K.GREEN, t("dash_going")
        p.circle(x + 4, y + 17, 4, dot)
        label = t("dash_resume") if app.paused else t("dash_pause")
        bw = 14 + 13 + 8 + p.measure(label, BUTTON) + (8 + 13 if not app.paused else 0) + 14
        bx = x + w - bw
        p.text(x + 16, y + (34 - 13 * 1.3) / 2, text, LIVE, max_w=bx - x - 28)
        p.rrect(bx, y, bw, 34, 10, K.BTN_STAGE, outline=K.BTN_STAGE_LINE)
        p.icon("play" if app.paused else "pause", bx + 14, y + 10.5, 13, K.TEXT, stroke=2.6)
        p.text(bx + 14 + 13 + 8, y + (34 - 13 * 1.3) / 2, label, BUTTON)
        if app.paused:
            regions.append(K.Region(bx, y, bx + bw, y + 34, self._resume, "resume"))
            return
        p.icon("down", bx + bw - 14 - 13, y + 10.5, 13, K.TEXT, stroke=2.2)
        options = [("hour", t("pause_hour")), ("forever", t("pause_forever"))]
        zoom, dx = self._place      # ampliado em tela cheia, a lista cresce junto e abre no mesmo lugar

        def open_menu():
            if self.host:
                self.host.open_menu(dx + (bx + bw - 220) * zoom, (y + 34 + 4) * zoom, 220, options, None, self._pause,
                                    above=(y - 4) * zoom, zoom=zoom)
        regions.append(K.Region(bx, y, bx + bw, y + 34, open_menu, "pause"))

    # ---- o cartão, à direita ----
    def _empty_text(self, t: Translator, state) -> str | None:
        if not state:
            return t("dash_empty_closed")
        if self.app.paused:
            return t("dash_empty_paused")
        if not self.app.discord_connected:
            return t("dash_empty_discord")
        return None if self.app.showing else t("dash_going")

    def _right_height(self, m: K.Painter, t: Translator, state) -> float:
        empty = self._empty_text(t, state)
        if empty:
            return 22 + K.paragraph_height(m, empty, EMPTY, CARD_W - 36) + 22
        return K.discord_card_height(0) + 12 + 16

    def _draw_right(self, p: K.Painter, x: float, y: float, t: Translator, state) -> None:
        empty = self._empty_text(t, state)
        if empty:
            h = 22 + K.paragraph_height(p, empty, EMPTY, CARD_W - 36) + 22
            p.dashed_rrect(x, y, CARD_W, h, 8, K.EMPTY_LINE)
            ty = y + 22
            for line in p.wrap(empty, EMPTY, CARD_W - 36):
                p.text(x + CARD_W / 2, ty, line, EMPTY, anchor="m")
                ty += EMPTY.size * EMPTY.line
            return
        showing = self.app.showing
        activity = showing["activity"]
        verb = t(f"verb_{VERBS.get(activity.get('type'), 'playing')}")
        start = (activity.get("timestamps") or {}).get("start", self.now() * 1000) / 1000
        elapsed = int(max(0, self.now() - start))
        clock = f"{elapsed // 3600}:{elapsed // 60 % 60:02d}:{elapsed % 60:02d}" if elapsed >= 3600 \
            else f"{elapsed // 60:02d}:{elapsed % 60:02d}"
        lines = ["Guitar Rig 7", activity.get("details", ""), activity.get("state", ""), t("elapsed", t=clock)]
        y += K.discord_card(p, x, y, CARD_W, verb, lines, []) + 12
        count, index = showing.get("count", 1), showing.get("index", 0)
        px_ = x
        for i in range(count):
            p.rrect(px_, y + 5, 16, 4, 2, K.AMBER if i == index else K.SCROLL_THUMB)
            px_ += 22
        if count > 1:
            left = max(0, math.ceil(showing.get("rotate", 20) - (self.now() - showing.get("sent_at", self.now()))))
            text = t("dash_rotation", i=index + 1, n=count, s=left)
        else:
            text = t("dash_rotation_one")
        p.text(px_ + 2, y, text, ROTATION, max_w=CARD_W - (px_ - x))

    # ---- meta do dia ----
    def _goal(self) -> int:
        try:
            return max(0, int(self.app.config["daily_goal_minutes"] or 0))
        except (TypeError, ValueError):
            return 0

    def _goal_note(self, t: Translator, state) -> str:
        today = self.today()
        goal = self._goal()
        played = self.app.stats.seconds_on(today)
        yesterday = self.app.stats.seconds_on(today - timedelta(days=1))
        after = f" {t('dash_yesterday', t=format_time(yesterday))}" if yesterday >= 60 else ""
        if not goal:
            return t("dash_no_goal")
        if played >= goal * 60:
            return t("dash_goal_done") + after
        if played < 60:
            streak = self.app.stats.summary(today=today).streak
            return t("dash_goal_still") + (f" {t('dash_streak_today', n=streak + 1)}" if streak >= 1 else "")
        return t("dash_goal_left", t=format_time(goal * 60 - played)) + after

    def _draw_goal(self, p: K.Painter, x: float, y: float, w: float, t: Translator, note: str) -> None:
        goal = self._goal()
        played = self.app.stats.seconds_on(self.today())
        minutes = int(played // 60)
        baseline = y + p.ascent(BIG)
        bw = p.baseline_text(x, baseline, str(minutes), BIG)
        p.baseline_text(x + bw + 6, baseline, t("dash_goal_of", n=goal) if goal else t("dash_today_only"), BIG_SUB)
        y += 34 + 12
        p.rrect(x, y, w, 10, 5, K.TRACK)
        frac = min(1.0, played / (goal * 60)) if goal else 0.0
        if frac > 0:
            fw = max(10, w * frac)
            p.rrect(x, y, fw, 10, 5, K.gradient(p.px(fw), p.px(10), K.AMBER, K.ORANGE, horizontal=True))
        p.paragraph(x, y + 10 + 10, note, NOTE, w)

    # ---- conexões ----
    def _connections(self, t: Translator, state) -> list[tuple[str, str, str, str | None]]:
        """(cor do ponto, nome, estado, explicação) de cada linha."""
        app = self.app
        discord = ((K.GREEN, t("conn_discord"), t("conn_on"), None) if app.discord_connected else
                   (K.ORANGE, t("conn_discord"), t("conn_off"), t("conn_discord_hint")))
        if not state:
            return [discord, (K.DIM, t("conn_gr"), t("conn_closed"), None),
                    (K.DIM, t("conn_screen"), t("screen_waiting"), None)]
        target = state[1]
        if target.kind == "plugin":
            return [discord, (K.GREEN, t("conn_gr"), t("conn_daw", host=target.host or "DAW"), None),
                    (K.DIM, t("conn_screen"), t("screen_plugin"), t("screen_plugin_hint"))]
        screen = {
            "minimized": (K.AMBER, t("screen_minimized"), t("screen_minimized_hint")),
            "no_ocr": (K.AMBER, t("screen_no_ocr"), t("screen_no_ocr_hint")),
        }.get(app.screen, (K.GREEN, t("screen_reading"), None))
        return [discord, (K.GREEN, t("conn_gr"), t("conn_open"), None),
                (screen[0], t("conn_screen"), screen[1], screen[2])]

    def _conn_height(self, m: K.Painter, rows: list, w: float) -> float:
        h = 0.0
        for i, (_dot, _name, _state, hint) in enumerate(rows):
            h += (0 if i == 0 else 8) + 13.5 * 1.3 + 8
            if hint:
                h += 2 + K.paragraph_height(m, hint, CONN_HINT, w - 20)
        return h

    def _draw_connections(self, p: K.Painter, x: float, y: float, w: float, rows: list) -> None:
        for i, (dot, name, state, hint) in enumerate(rows):
            if i:
                p.hline(x, x + w, y, K.PANEL_LINE)
                y += 8
            p.circle(x + 4, y + 13.5 * 1.3 / 2, 4, dot)
            p.text(x + w, y, state, CONN_R, anchor="r")
            p.text(x + 20, y, name, CONN)
            y += 13.5 * 1.3
            if hint:
                y += 2 + p.paragraph(x + 20, y + 2, hint, CONN_HINT, w - 20)
            y += 8
