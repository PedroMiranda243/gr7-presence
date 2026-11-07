"""Página Atualização da janela principal, como no exemplo aprovado (Palco).

Aberta pelo item da versão nova no pé da barra lateral, pelo menu da bandeja ou pelo aviso. Mostra a
versão em destaque, o que muda (o trecho do CHANGELOG que vira a nota da release) e como funciona.
"Atualizar agora" pede à bandeja para baixar; o andamento chega por `set_progress` e, se der errado,
por `show_error`. Quem troca os arquivos continua sendo o `tools/atualizar.py` (decisão D7).
"""
from __future__ import annotations

import re
import webbrowser
from typing import Callable

from . import ui_kit as K
from .i18n import Translator

PAD_X, PAD_TOP, PAD_BOTTOM, GAP = 24, 20, 20, 14
TITLE = K.Style(46, 800, K.GLOW, display=True, width=125, line=0.98)
META = K.Style(14, 400, K.TEXT_LEAD, line=1.5)
PRIMARY = K.Style(13.5, 700, K.ON_ACCENT, line=1.3)
LINK = K.Style(13, 400, K.TEXT_SOFT, line=1.3)
PROGRESS = K.Style(13, 400, K.TEXT_LEAD, line=1.3)
ERROR = K.Style(13, 400, K.BAD, line=1.45)
H3 = K.Style(15, 700, K.TEXT, display=True, width=112, line=1.2)
H4 = K.Style(13, 700, K.TEXT, line=1.3)
ITEM = K.Style(13.5, 400, K.TEXT_SOFT, line=1.55)
NOTE = K.Style(13, 400, K.MUTED, line=1.45)
LIGHT = [(0.0, (255, 183, 77, 0.34)), (0.42, (255, 106, 61, 0.14)), (0.74, (17, 19, 26, 0.0)), (1.0, (17, 19, 26, 0.0))]
SKIP_SECTIONS = {"como atualizar", "how to update"}   # dentro do programa, a pessoa já está atualizando


def note_sections(markdown: str) -> list[tuple[str, list[tuple[str, int]]]]:
    """As notas da release em seções, sem o markdown: [(título, [(item, nível)])]; nível 1 é o subitem."""
    sections: list[tuple[str, list[list]]] = []
    for raw in (markdown or "").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            sections.append((line.lstrip("#").strip(), []))
        elif line.startswith(("- ", "* ")):
            if not sections:
                sections.append(("", []))
            sections[-1][1].append([line[2:].strip(), 1 if raw.startswith(" ") else 0])
        elif line and sections and sections[-1][1] and raw.startswith(" "):
            sections[-1][1][-1][0] += " " + line          # continuação do item na linha de baixo
    clean = lambda s: re.sub(r"`([^`]*)`", r"\1", re.sub(r"\*\*(.+?)\*\*", r"\1", s)).replace("\uFE0F", "")
    return [(clean(title), [(clean(text), level) for text, level in items]) for title, items in sections
            if items and title.lower() not in SKIP_SECTIONS]


class UpdatePage:
    key = "update"
    icon = "up"
    label_key = "nav_update"
    rail = False          # tem o seu próprio item no pé da barra lateral

    def __init__(self, release: Callable[[], object], current: str, on_confirm: Callable[[object], None],
                 on_later: Callable[[], None], open_url: Callable[[str], object] = webbrowser.open):
        self.release = release
        self.current = current
        self.on_confirm = on_confirm
        self.on_later = on_later
        self.open_url = open_url
        self.on_change: Callable[[], None] = lambda: None
        self.host = None
        self.state = "idle"            # idle, downloading, ready, error
        self.done = 0
        self.total: int | None = None
        self.error = ""

    # ---- chamados pela bandeja ------------------------------------------------------------------
    def set_progress(self, done: int, total: int | None) -> None:
        self.state, self.done, self.total = "downloading", done, total
        self.on_change()

    def set_ready(self) -> None:
        self.state = "ready"
        self.on_change()

    def show_error(self, message: str) -> None:
        self.state, self.error = "error", message
        self.on_change()

    def _confirm(self) -> None:
        release = self.release()
        if release is None or self.state in ("downloading", "ready"):
            return
        self.state, self.done, self.total = "downloading", 0, getattr(release, "size", None)
        self.on_change()
        self.on_confirm(release)

    # ---- desenho -------------------------------------------------------------------------------
    @staticmethod
    def _mb(size: int, t: Translator) -> str:
        return f"{size / 1_048_576:.1f}".replace(".", t("decimal_sep")) + " MB"

    def render(self, width: float, scale: float, t: Translator) -> K.Rendered:
        release = self.release()
        m = K.Painter(1, 1, scale)
        inner = width - 2 * PAD_X
        text_w = inner - 60
        if release is None:   # a versão já foi instalada, ou a página foi aberta sem versão nova
            sections, version, size = [], self.current, None
        else:
            sections, version, size = note_sections(release.notes), release.version, release.size
        meta = (t("upd_meta", current=self.current, size=self._mb(size, t)) if size
                else t("upd_meta_nosize", current=self.current))
        title_lines = m.balanced(t("upd_title", version=version), TITLE, text_w)
        head_h = 6 + len(title_lines) * TITLE.size * TITLE.line + 12 + K.paragraph_height(m, meta, META, text_w)
        head_h += 22 + 38
        if self.state != "idle":
            head_h += 20 + (K.paragraph_height(m, t("update_failed", error=self.error), ERROR, text_w)
                            if self.state == "error" else 13 * 1.3 + 8 + 10)
        stage_h = 30 + head_h + 26
        col = (inner - GAP) / 2
        notes_h = 2 + 36 + 18 + 12 + self._notes_height(m, sections, col - 42, t)
        how = [t("upd_how_1"), t("upd_how_2"), t("upd_how_3", current=self.current)]
        how_h = 2 + 36 + 18 + 12 + sum(K.paragraph_height(m, s, NOTE, col - 42) + 10 for s in how) - 10
        # Os dois cartões têm a mesma altura quando cabem juntos, como no exemplo. Com notas compridas,
        # "Como funciona" fica do tamanho dele, em vez de um painel vazio comprido.
        stretch = max(notes_h, how_h) <= 2 * min(notes_h, how_h)
        notes_box = max(notes_h, how_h) if stretch else notes_h
        how_box = max(notes_h, how_h) if stretch else how_h
        row_h = max(notes_h, how_h)
        total = PAD_TOP + stage_h + GAP + row_h + PAD_BOTTOM

        p = K.Painter(width, total, scale)
        regions: list[K.Region] = []
        light = K.radial_light(p.px(inner), p.px(stage_h), p.px(inner * 0.2), p.px(-stage_h * 0.3),
                               p.px(inner * 0.6), p.px(stage_h * 1.4), LIGHT)
        y = PAD_TOP
        p.rrect(PAD_X, y, inner, stage_h, 18, K.STAGE, light=light)
        x = PAD_X + 30
        ty = y + 30 + 6
        for line in title_lines:
            p.text(x, ty, line, TITLE)
            ty += TITLE.size * TITLE.line
        ty += 12
        ty += p.paragraph(x, ty, meta, META, text_w) + 22
        busy = self.state in ("downloading", "ready")
        bw = p.measure(t("update_now"), PRIMARY) + 36
        fill = K.gradient(p.px(bw), p.px(38), K.AMBER, K.ORANGE, horizontal=True)
        if busy or release is None:
            fill = fill.point(lambda v: round(v * 0.45 + 17 * 0.55))   # apagado, como o :disabled do exemplo
        p.rrect(x, ty, bw, 38, 11, fill)
        p.text(x + 18, ty + (38 - 13.5 * 1.3) / 2, t("update_now"), PRIMARY,
               color=K.ON_ACCENT if not busy and release else K.ON_ACCENT_OFF)
        if not busy and release is not None:
            regions.append(K.Region(x, ty, x + bw, ty + 38, self._confirm, "update_now"))
        lx = x + bw + 10
        later = t("upd_later")
        lw = p.measure(later, K.BUTTON) + 28
        p.rrect(lx, ty + 2, lw, 34, 10, K.BTN_STAGE, outline=K.BTN_STAGE_LINE)
        p.text(lx + 14, ty + 2 + (34 - 13 * 1.3) / 2, later, K.BUTTON, color=K.TEXT if not busy else K.FAINT)
        if not busy:
            regions.append(K.Region(lx, ty + 2, lx + lw, ty + 36, self.on_later, "later"))
        if release is not None:
            gw = p.text(x + text_w, ty + (38 - 13 * 1.3) / 2, t("update_page"), LINK, anchor="r")
            ux = x + text_w - gw
            p.hline(ux, x + text_w, ty + (38 - 13 * 1.3) / 2 + 13 * 1.3 - 1, K.TEXT_SOFT)
            regions.append(K.Region(ux, ty, x + text_w, ty + 38, lambda: self.open_url(release.url), "github"))
        ty += 38
        if self.state == "error":
            p.paragraph(x, ty + 20, t("update_failed", error=self.error), ERROR, text_w)
        elif self.state != "idle":
            ty += 20
            if self.state == "ready":
                label, amount, frac = t("upd_checked"), "", 1.0
            else:
                label = t("upd_downloading")
                amount = (t("upd_progress", done=self._mb(self.done, t), total=self._mb(self.total, t))
                          if self.total else self._mb(self.done, t))
                frac = min(1.0, self.done / self.total) if self.total else 0.0
            p.text(x, ty, label, PROGRESS)
            if amount:
                p.text(x + text_w, ty, amount, PROGRESS, anchor="r")
            ty += 13 * 1.3 + 8
            p.rrect(x, ty, text_w, 10, 5, K.TRACK)
            if frac > 0:
                fw = max(10, text_w * frac)
                p.rrect(x, ty, fw, 10, 5, K.gradient(p.px(fw), p.px(10), K.AMBER, K.ORANGE, horizontal=True))
        y += stage_h + GAP

        cx, cy, cw = self._panel(p, PAD_X, y, col, notes_box, t("upd_notes_title"))
        self._draw_notes(p, cx, cy, cw, sections, t)
        cx, cy, cw = self._panel(p, PAD_X + col + GAP, y, col, how_box, t("upd_how_title"))
        for s in how:
            cy += p.paragraph(cx, cy, s, NOTE, cw) + 10
        return K.Rendered(p.img, total, regions)

    def _panel(self, p: K.Painter, x: float, y: float, w: float, h: float, title: str) -> tuple[float, float, float]:
        p.rrect(x, y, w, h, 16, K.PANEL, outline=K.PANEL_LINE)
        p.text(x + 21, y + 19, title, H3)
        return x + 21, y + 19 + 18 + 12, w - 42

    def _notes_height(self, m: K.Painter, sections: list, w: float, t: Translator) -> float:
        if not sections:
            return K.paragraph_height(m, t("update_window_no_notes"), NOTE, w)
        h = 0.0
        for i, (title, items) in enumerate(sections):
            h += (14 if i else 0) + (13 * 1.3 + 6 if title else 0)
            h += sum(K.paragraph_height(m, item, ITEM, w - 18 - 18 * level) for item, level in items)
        return h

    def _draw_notes(self, p: K.Painter, x: float, y: float, w: float, sections: list, t: Translator) -> None:
        if not sections:
            p.paragraph(x, y, t("update_window_no_notes"), NOTE, w)
            return
        for i, (title, items) in enumerate(sections):
            y += 14 if i else 0
            if title:
                p.text(x, y, title, H4)
                y += 13 * 1.3 + 6
            for item, level in items:
                ix = x + 18 * level
                p.circle(ix + 6, y + 13.5 * 1.55 / 2, 2.5, K.AMBER)
                if level:   # subitem: bolinha vazada
                    p.circle(ix + 6, y + 13.5 * 1.55 / 2, 1.3, K.PANEL)
                y += p.paragraph(ix + 18, y, item, ITEM, w - 18 - 18 * level)
