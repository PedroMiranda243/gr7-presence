"""Página Ajustes da janela principal: tudo o que antes só dava para mudar no config.json.

Cada opção grava na hora (`Config.update`) e o loop reaplica na volta seguinte, sem reiniciar. Do lado
direito, fixa, a prévia do perfil: os cartões são montados pelas mesmas funções que mandam a atividade
ao Discord (`build_cards` e `build_activity`), então a prévia mostra o que o Discord vai receber.
"""
from __future__ import annotations

import copy
import logging
import os
import threading
import time
from typing import Callable

from . import __version__
from . import autostart as autostart_mod
from . import ui_kit as K
from .app import MIN_ROTATE_SECONDS
from .config import DATA_DIR
from .detector import Target
from .gr7_state import PresetInfo
from .i18n import Translator, format_time
from .presence import build_activity, build_cards

log = logging.getLogger(__name__)

PAD_LEFT, PAD_RIGHT, PAD_TOP, PAD_BOTTOM, GAP = 24, 8, 20, 24, 14
SIDE_W = 344                 # 20 de espaço + 300 da prévia + 24 de margem
ROTATE_MAX = 60
SLIDER_W = 150
MIN_ROTATE = int(MIN_ROTATE_SECONDS)   # limite do Discord (AGENTS.md, regra 7)
GOALS = [0, 15, 20, 30, 45, 60, 90, 120]

TITLE = K.Style(30, 800, K.TEXT, display=True, width=125, line=1.0)
H3 = K.Style(15, 700, K.TEXT, display=True, width=112, line=1.2)
LABEL = K.Style(13.5, 600, K.TEXT, line=1.3)
HINT = K.Style(12.5, 400, K.MUTED, line=1.4)
NOTE = K.Style(13, 400, K.MUTED, line=1.45)
SMALL = K.Style(12, 400, K.MUTED, line=1.3)
COUNT = K.Style(11.5, 400, K.FAINT, line=1.3)
ERROR = K.Style(12.5, 400, K.BAD, line=1.4)
VALUE = K.Style(13, 400, K.TEXT, line=1.3)
SIDE_HINT = K.Style(12.5, 400, K.MUTED, line=1.45)
ROTATION = K.Style(12, 400, K.MUTED, line=1.3)


def valid_url(url: str) -> bool:
    """O mesmo critério do presence.build_activity: sem isso, o Discord descarta a atividade inteira."""
    url = url.strip()
    return url.startswith(("https://", "http://")) and len(url) <= 512 and "." in url


class SettingsPage:
    key = "settings"
    icon = "sliders"
    label_key = "nav_settings"
    side_width = SIDE_W

    def __init__(self, config, stats, library=None, app_state: Callable[[], tuple | None] = lambda: None,
                 autostart=autostart_mod, open_path: Callable[[object], None] = os.startfile):
        self.config = config
        self.stats = stats
        self.library = library
        self.app_state = app_state
        self.autostart = autostart
        self.open_path = open_path
        self.on_change: Callable[[], None] = lambda: None
        self.host = None
        self.focused: str | None = None
        self.card_index = 0
        self._rotate: int | None = None          # valor enquanto arrasta, gravado ao soltar
        self._autostart_wanted: bool | None = None
        self._buttons: list[dict] | None = None   # cópia enquanto a pessoa digita
        self._samples: dict[str, PresetInfo | None] = {}

    # ---- valores ------------------------------------------------------------------------------
    def _set(self, key: str, value) -> None:
        self.config.update(key, value)
        self.on_change()

    def _toggle(self, key: str) -> None:
        self._set(key, not self.config[key])

    def _rotate_value(self) -> int:
        if self._rotate is not None:
            return self._rotate
        try:
            return max(MIN_ROTATE, min(ROTATE_MAX, int(self.config["rotate_seconds"] or 20)))
        except (TypeError, ValueError):
            return 20

    def buttons(self) -> list[dict]:
        if self._buttons is not None:
            return self._buttons
        saved = self.config["buttons"] if isinstance(self.config["buttons"], list) else []
        out = [{"label": str((b or {}).get("label") or ""), "url": str((b or {}).get("url") or "")}
               for b in saved[:2] if isinstance(b, dict)]
        return out + [{"label": "", "url": ""} for _ in range(2 - len(out))]

    def _edit_button(self, index: int, part: str, text: str) -> None:
        if self._buttons is None:
            self._buttons = copy.deepcopy(self.buttons())
        self._buttons[index][part] = text
        if self.host:   # grava quando a pessoa para de digitar, para não reenviar o cartão a cada letra
            self.host.later(700, self._save_buttons, key="buttons")
        self.on_change()

    def _save_buttons(self) -> None:
        if self._buttons is not None:
            self.config.update("buttons", self._buttons)
            self._buttons = None
            self.on_change()

    def focus_field(self, key: str | None) -> None:
        if key is None and self.focused and self.focused.startswith("btn"):
            self._save_buttons()
        self.focused = key
        self.on_change()

    def _autostart_on(self) -> bool:
        if self._autostart_wanted is not None:
            return self._autostart_wanted
        try:
            return self.autostart.is_enabled()
        except OSError:
            return False

    def _toggle_autostart(self) -> None:
        wanted = not self._autostart_on()
        self._autostart_wanted = wanted   # mostra na hora; o atalho é criado numa thread (leva ~1 s)

        def run():
            try:
                self.autostart.set_enabled(wanted)
            except Exception:
                log.exception("Não consegui mudar o início com o Windows")
            self._autostart_wanted = None
        threading.Thread(target=run, name="autostart", daemon=True).start()
        self.on_change()

    def _open_config(self) -> None:
        if not self.config.path.exists():
            self.config.save()
        self.open_path(self.config.path)

    # ---- controle deslizante --------------------------------------------------------------------
    def _drag_rotate(self, x0: float, x: float) -> None:
        frac = (x - x0 - 8) / (SLIDER_W - 16)
        value = MIN_ROTATE + int(max(0.0, min(1.0, frac)) * (ROTATE_MAX - MIN_ROTATE) / 5 + 0.5) * 5   # de 5 em 5
        if value != self._rotate:
            self._rotate = int(value)
            self.on_change()

    def end_drag(self) -> None:
        if self._rotate is not None:
            value, self._rotate = self._rotate, None
            self._set("rotate_seconds", value)

    # ---- a prévia ---------------------------------------------------------------------------------
    def _sample(self, t: Translator) -> PresetInfo:
        """Com o Guitar Rig fechado: o último preset tocado (lido da biblioteca numa thread), ou um exemplo."""
        recent = self.stats.summary(top=1, recent=1).recent
        last = recent[0] if recent else {}
        name = last.get("last_preset")
        if not name:
            return PresetInfo(name=t("sample_preset"), amp="Jump", chain=["Noise Gate", "Jump", "Matched Cabinet Pro",
                              "Studio Reverb"], genres=["Rock"], characters=["Clean"])
        if name not in self._samples and self.library is not None:
            self._samples[name] = None

            def load():
                try:
                    self._samples[name] = self.library.load(name)
                except Exception:
                    log.debug("Sem o preset %s para a prévia", name, exc_info=True)
            threading.Thread(target=load, name="previa", daemon=True).start()
        amp = last.get("last_amp")
        return self._samples.get(name) or PresetInfo(name=name, amp=amp, chain=[amp] if amp else [])

    def preview(self, t: Translator) -> tuple[list[dict], Target]:
        """As atividades que o Discord receberia, uma por cartão, como o loop monta."""
        state = self.app_state()
        if state:
            preset, target, tracks, rack_state = state
        else:
            preset, target, tracks, rack_state = self._sample(t), Target("standalone", 0, time.time() - 2535), [], None
        summary = self.stats.summary() if self.config["show_stats"] else None
        cards = build_cards(preset, target, summary, self.config, t, tracks, rack_state)
        return [build_activity(c, target, self.config, t, None, None) for c in cards], target

    # ---- desenho do formulário -----------------------------------------------------------------
    def render(self, width: float, scale: float, t: Translator) -> K.Rendered:
        m = K.Painter(1, 1, scale)
        inner = width - PAD_LEFT - PAD_RIGHT
        sections = self._sections(t, m, inner - 42)
        total = PAD_TOP + 30 + GAP + sum(h + GAP for _title, h, _draw in sections) - GAP + PAD_BOTTOM
        p = K.Painter(width, total, scale)
        regions: list[K.Region] = []
        fields: list[K.Field] = []
        p.text(PAD_LEFT, PAD_TOP, t("settings_heading"), TITLE)
        y = PAD_TOP + 30 + GAP
        for title, h, draw in sections:
            p.rrect(PAD_LEFT, y, inner, h, 16, K.PANEL, outline=K.PANEL_LINE)
            p.text(PAD_LEFT + 21, y + 19, title, H3)
            draw(p, PAD_LEFT + 21, y + 19 + 18 + 12, inner - 42, regions, fields)
            y += h + GAP
        return K.Rendered(p.img, total, regions, fields)

    def _sections(self, t: Translator, m: K.Painter, w: float) -> list[tuple[str, float, Callable]]:
        show = [(k, t(f"set_{name}"), t(f"set_{name}_hint")) for k, name in (
            ("show_preset", "preset"), ("show_rack_chain", "chain"), ("show_tags", "tags"),
            ("show_backing_track", "tape"), ("show_stats", "stats"), ("show_streak", "streak"))]
        rows_show = [self._switch_row(t, k, label, hint) for k, label, hint in show]

        activities = [(k, t(f"activity_{k}")) for k in ("playing", "listening", "watching", "competing")]
        displays = [(k, t(f"display_{k}")) for k in ("name", "details", "state")]
        rows_look = [
            self._select_row("activity_type", t("set_activity"), t("set_activity_hint"), activities),
            self._select_row("status_display", t("set_display"), t("set_display_hint"), displays),
            self._slider_row(t),
        ]
        goal = self._goal()
        goals = [(g, t("goal_none") if g == 0 else f"{g} min" if g < 90 else format_time(g * 60))   # "60 min", "1 h 30"
                 for g in sorted(set(GOALS + [goal]))]
        rows_practice = [
            self._select_row("daily_goal_minutes", t("set_goal"), t("set_goal_hint"), goals, current=goal),
            self._switch_row(t, "notify_goal", t("set_goal_note"), t("set_goal_note_hint")),
        ]
        rows_program = [
            self._language_row(t),
            self._switch_row(t, None, t("set_autostart"), "", get=self._autostart_on, toggle=self._toggle_autostart),
            self._switch_row(t, "detect_plugin_hosts", t("set_daw"), t("set_daw_hint")),
            self._switch_row(t, "notify_minimized", t("set_min_note"), t("set_min_note_hint")),
            self._switch_row(t, "check_updates", t("set_updates"), t("set_updates_hint")),
            self._advanced_row(t),
        ]
        out = []
        for title, rows in ((t("set_section_show"), rows_show), (t("set_section_look"), rows_look),
                            (t("set_section_practice"), rows_practice), (t("set_section_program"), rows_program)):
            heights = [self._row_height(m, w, row) for row in rows]
            out.append((title, 2 + 36 + 18 + 12 + sum(heights) - 9, self._rows_drawer(rows, heights)))
        buttons_h = self._buttons_height(m, w, t)
        out.insert(2, (t("set_section_buttons"), 2 + 36 + 18 + 12 + buttons_h, self._buttons_drawer(t)))
        return out

    def _goal(self) -> int:
        try:
            return max(0, int(self.config["daily_goal_minutes"] or 0))
        except (TypeError, ValueError):
            return 0

    # Cada linha: (rótulo, dica, largura do controle, altura do controle, desenho do controle).
    def _switch_row(self, t, key, label, hint, get=None, toggle=None):
        get = get or (lambda: bool(self.config[key]))
        toggle = toggle or (lambda: self._toggle(key))

        def draw(p, x, y, regions, _fields):
            K.switch(p, x, y, get())
            regions.append(K.Region(x - 4, y - 6, x + 42, y + 28, toggle, key or label))
        return label, hint, 38, 22, draw

    def _select_row(self, key, label, hint, options, current=None):
        def draw(p, x, y, regions, _fields, width):
            value = self.config[key] if current is None else current
            text = next((lbl for v, lbl in options if v == value), str(value))
            K.select_box(p, x, y, width, text, focused=self.focused == key)

            def pick(v):
                self.focused = None
                self._set(key, v)

            def open_menu():
                if self.host:
                    self.focused = key
                    self.on_change()
                    self.host.open_menu(x, y + 34 + 4, width, options, value, pick)
            regions.append(K.Region(x, y, x + width, y + 34, open_menu, key))
        return label, hint, ("select", [lbl for _v, lbl in options]), 34, draw

    def _slider_row(self, t):
        def draw(p, x, y, regions, _fields):
            value = self._rotate_value()
            K.slider(p, x, y + 6, SLIDER_W, (value - MIN_ROTATE) / (ROTATE_MAX - MIN_ROTATE))
            p.text(x + SLIDER_W + 10 + 40, y + (34 - 13 * 1.3) / 2, t("seconds_short", n=value), VALUE, anchor="r")
            regions.append(K.Region(x - 4, y, x + SLIDER_W + 4, y + 34, lambda: None, "rotate_seconds",
                                    drag=lambda px, _py: self._drag_rotate(x, px)))
        return t("set_rotate"), t("set_rotate_hint"), SLIDER_W + 10 + 40, 34, draw

    def _language_row(self, t):
        labels = [t("lang_pt"), t("lang_en")]
        width = sum(K.Painter(1, 1, 1).measure(lbl, K.Style(12.5, 600)) + 24 for lbl in labels) + 2 + 8

        def draw(p, x, y, regions, _fields):
            langs = ["pt", "en"]
            current = langs.index(self.config["language"]) if self.config["language"] in langs else 0
            _w, _h, segs = K.segmented(p, x + width, y, labels, current, langs,
                                       [lambda lang=lang: self._set("language", lang) for lang in langs])
            regions.extend(segs)
        return t("set_language"), "", width, 36, draw

    def _advanced_row(self, t):
        labels = [t("set_open_config"), t("set_open_logs")]
        m = K.Painter(1, 1, 1)
        widths = [m.measure(lbl, K.BUTTON) + 28 for lbl in labels]
        width = sum(widths) + 8

        def draw(p, x, y, regions, _fields):
            bx = x
            for label, bw, action in zip(labels, widths, (self._open_config, lambda: self.open_path(DATA_DIR))):
                K.button(p, bx, y, label)
                regions.append(K.Region(bx, y, bx + bw, y + 34, action, label))
                bx += bw + 8
        return t("set_advanced"), t("set_advanced_hint", version=__version__), width, 34, draw

    def _control_width(self, m: K.Painter, row) -> float:
        width = row[2]
        if isinstance(width, tuple):   # campo de escolha: do tamanho da opção mais comprida
            return K.select_width(m, width[1])
        return width

    def _row_height(self, m: K.Painter, w: float, row) -> float:
        label, hint, _cw, ch, _draw = row
        text_w = w - self._control_width(m, row) - 18
        text_h = len(m.wrap(label, LABEL, text_w)) * LABEL.size * LABEL.line
        if hint:
            text_h += 3 + K.paragraph_height(m, hint, HINT, text_w)
        return 11 + max(text_h, ch) + 11

    def _rows_drawer(self, rows, heights):
        def draw(p: K.Painter, x: float, y: float, w: float, regions: list, fields: list) -> None:
            top = y - 9   # a primeira linha começa colada no título (padding 2 em vez de 11)
            for i, (row, h) in enumerate(zip(rows, heights)):
                label, hint, _cw, ch, control = row
                cw = self._control_width(p, row)
                if i:
                    p.hline(x, x + w, top, K.PANEL_LINE)
                text_w = w - cw - 18
                ty = top + 11
                for line in p.wrap(label, LABEL, text_w):
                    p.text(x, ty, line, LABEL)
                    ty += LABEL.size * LABEL.line
                if hint:
                    p.paragraph(x, ty + 3, hint, HINT, text_w)
                cx, cy = x + w - cw, top + (h - ch) / 2
                if isinstance(row[2], tuple):
                    control(p, cx, cy, regions, fields, cw)
                else:
                    control(p, cx, cy, regions, fields)
                top += h
        return draw

    # ---- botões do perfil ----
    def _buttons_height(self, m: K.Painter, w: float, t: Translator) -> float:
        h = K.paragraph_height(m, t("set_buttons_hint"), NOTE, w) - 4 + 10
        for i, b in enumerate(self.buttons()):
            h += (2 if i == 0 else 10) + 15.6 + 5 + 34 + 15 + 10
            if b["url"].strip() and not valid_url(b["url"]):
                h += K.paragraph_height(m, t("set_button_error"), ERROR, w) + 4
        return h

    def _buttons_drawer(self, t: Translator):
        def draw(p: K.Painter, x: float, y: float, w: float, regions: list, fields: list) -> None:
            y += p.paragraph(x, y - 4, t("set_buttons_hint"), NOTE, w) - 4 + 10
            col1 = (w - 8) / 2.4
            col2 = w - 8 - col1
            for i, b in enumerate(self.buttons()):
                if i:
                    p.hline(x, x + w, y, K.PANEL_LINE)
                top = y + (2 if i == 0 else 10)
                bad = bool(b["url"].strip()) and not valid_url(b["url"])
                p.text(x, top, t("set_button_label", n=i + 1), SMALL)
                p.text(x + col1 + 8, top, t("set_button_link"), SMALL)
                fy = top + 15.6 + 5
                for part, fx, fw, placeholder, max_len in (("label", x, col1, t("set_button_placeholder"), 32),
                                                           ("url", x + col1 + 8, col2, "https://", 512)):
                    key = f"btn{i}_{part}"
                    K.text_box(p, fx, fy, fw, 34, focused=self.focused == key, bad=part == "url" and bad)
                    fields.append(K.Field(key, fx, fy, fw, 34, b[part], placeholder, max_len,
                                          lambda text, i=i, part=part: self._edit_button(i, part, text)))
                p.text(x + col1, fy + 34 - 2, f"{len(b['label'])}/32", COUNT, anchor="r")
                y = fy + 34 + 15
                if bad:
                    y += 4
                    y += p.paragraph(x, y, t("set_button_error"), ERROR, w)
                y += 10
        return draw

    # ---- o painel fixo da direita -----------------------------------------------------------------
    def render_side(self, width: float, height: float, scale: float, t: Translator) -> K.Rendered:
        p = K.Painter(width, height, scale)
        regions: list[K.Region] = []
        x, w = 20, width - 20 - 24
        y = 20
        p.text(x, y, t("preview_title"), H3)
        y += 18 + 12
        activities, target = self.preview(t)
        self.card_index %= len(activities)
        activity = activities[self.card_index]
        kind = self.config["activity_type"] if self.config["activity_type"] in ("playing", "listening", "watching",
                                                                                 "competing") else "playing"
        verb = t(f"verb_{kind}")
        display = self.config["status_display"]
        shown = activity.get("details", "") if display == "details" else activity.get("state", "") if display == "state" \
            else "Guitar Rig 7"
        y += K.member_row(p, x, y, w, t("preview_you"), f"{verb} {shown}") + 10
        elapsed = int(max(0, time.time() - target.started_at))
        clock = f"{elapsed // 3600}:{elapsed // 60 % 60:02d}:{elapsed % 60:02d}" if elapsed >= 3600 \
            else f"{elapsed // 60:02d}:{elapsed % 60:02d}"
        lines = ["Guitar Rig 7", activity.get("details", ""), activity.get("state", ""), t("elapsed", t=clock)]
        buttons = [b["label"] for b in activity.get("buttons", [])]
        y += K.discord_card(p, x, y, w, verb, lines, buttons) + 12
        px_ = x
        for i in range(len(activities)):
            p.rrect(px_, y + 5, 16, 4, 2, K.AMBER if i == self.card_index else K.SCROLL_THUMB)
            regions.append(K.Region(px_ - 2, y - 2, px_ + 18, y + 16, lambda i=i: self._show_card(i), f"card{i}"))
            px_ += 22
        p.text(px_ + 2, y, t("preview_rotation", i=self.card_index + 1, n=len(activities), s=self._rotate_value()),
               ROTATION, max_w=w - (px_ - x) - 2)
        y += 16 + 12
        p.paragraph(x, y, t("preview_hint"), SIDE_HINT, w)
        foot = height - 20 - 12.5 * 1.45
        p.circle(x + 4, foot + 12.5 * 1.45 / 2, 4, K.GREEN)
        p.text(x + 16, foot, t("preview_saved"), SIDE_HINT, max_w=w - 16)
        return K.Rendered(p.img, height, regions)

    def _show_card(self, index: int) -> None:
        self.card_index = index
        self.on_change()
