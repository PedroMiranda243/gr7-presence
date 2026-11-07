"""Primeira abertura: uma janela, uma vez, depois de instalar (ou de atualizar para a 1.4.0).

Confere se o Discord, o Guitar Rig e a leitura da tela estão prontos, mostra como o perfil vai ficar e
já pergunta a meta diária e se o programa inicia com o Windows. Como no exemplo aprovado (Palco).
"""
from __future__ import annotations

import importlib.util
import logging
import threading
import time
from pathlib import Path
from typing import Callable

import psutil

from . import autostart as autostart_mod
from . import ui_kit as K
from .app import DEFAULT_EXE as GUITAR_RIG_EXE
from .detector import Target
from .i18n import Translator
from .presence import build_activity, build_cards

log = logging.getLogger(__name__)

SIZE = (720, 568)   # área de dentro; com a barra de título, os 720 × 600 do exemplo
DEFAULT_EXE = Path(GUITAR_RIG_EXE)
DISCORD_PROCESSES = {"discord.exe", "discordptb.exe", "discordcanary.exe"}
GOALS = [0, 20, 30, 60]
TITLE = K.Style(38, 800, K.GLOW, display=True, width=125, line=1.0)
LEAD = K.Style(14, 400, "#D2CCC2", line=1.5)
CHECK = K.Style(13.5, 600, K.TEXT, line=1.3)
CHECK_HINT = K.Style(13, 400, K.MUTED, line=1.4)   # mesma largura do 12,5 do exemplo
LABEL = K.Style(13.5, 600, K.TEXT, line=1.3)
PREVIEW = K.Style(13, 400, "#D2CCC2", line=1.45)
FOOT = K.Style(13, 400, K.MUTED, line=1.3)
PRIMARY = K.Style(13.5, 700, "#1A0E08", line=1.3)
LIGHT = [(0.0, (255, 183, 77, 0.30)), (0.45, (255, 106, 61, 0.12)), (0.75, (11, 12, 16, 0.0)), (1.0, (11, 12, 16, 0.0))]
OK_BG, WARN_BG = "#122923", "#2A2416"


def discord_running() -> bool:
    try:
        return any((p.info.get("name") or "").lower() in DISCORD_PROCESSES for p in psutil.process_iter(["name"]))
    except psutil.Error:
        return False


def ocr_installed() -> bool:
    try:
        return importlib.util.find_spec("winrt.windows.media.ocr") is not None
    except (ImportError, ValueError):
        return False


class WelcomePage:
    key = "welcome"
    icon = "dash"
    label_key = "nav_dashboard"

    def __init__(self, config, stats, on_start: Callable[[], None], autostart=autostart_mod,
                 checks: Callable[[], tuple[bool, bool, bool]] | None = None, library=None):
        self.library = library
        self._loaded: dict = {}
        self.config = config
        self.stats = stats
        self.on_start = on_start
        self.autostart = autostart
        self.checks = checks or (lambda: (discord_running(), DEFAULT_EXE.exists(), ocr_installed()))
        self.on_change: Callable[[], None] = lambda: None
        self.host = None
        self.view_height = SIZE[1]
        self._autostart_wanted: bool | None = None
        self._checked = None

    def _goal(self) -> int:
        try:
            return int(self.config["daily_goal_minutes"] or 0)
        except (TypeError, ValueError):
            return 0

    def _set_goal(self, minutes: int) -> None:
        self.config.update("daily_goal_minutes", minutes)
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
        self._autostart_wanted = wanted

        def run():
            try:
                self.autostart.set_enabled(wanted)
            except Exception:
                log.exception("Não consegui mudar o início com o Windows")
            self._autostart_wanted = None
        threading.Thread(target=run, name="autostart", daemon=True).start()
        self.on_change()

    def _sample(self, t: Translator) -> list[str]:
        """O primeiro cartão, com o último preset tocado (ou um exemplo), como o Discord vai mostrar."""
        from .gr7_state import PresetInfo
        recent = self.stats.summary(top=1, recent=1).recent
        last = recent[0] if recent else {}
        name, amp = last.get("last_preset"), last.get("last_amp")
        if name and self.library is not None and name not in self._loaded:
            self._loaded[name] = None   # lê o preset (amp e cadeia) numa thread; a janela redesenha sozinha

            def load():
                try:
                    self._loaded[name] = self.library.load(name)
                except Exception:
                    log.debug("Sem o preset %s para a prévia", name, exc_info=True)
            threading.Thread(target=load, name="previa", daemon=True).start()
        preset = (self._loaded.get(name) or PresetInfo(name=name, amp=amp, chain=[amp] if amp else []) if name else
                  PresetInfo(name=t("sample_preset"), amp="Jump", chain=["Noise Gate", "Jump", "Matched Cabinet Pro"],
                             genres=["Rock"]))
        target = Target("standalone", 0, time.time() - 1)
        card = build_cards(preset, target, None, self.config, t)[0]
        activity = build_activity(card, target, self.config, t, None, None)
        return ["Guitar Rig 7", activity.get("details", ""), activity.get("state", ""), t("elapsed_one", t="00:01")]

    def render(self, width: float, scale: float, t: Translator) -> K.Rendered:
        if self._checked is None:   # uma vez por abertura da janela: procurar processos custa um pouco
            self._checked = self.checks()
        discord, guitar_rig, ocr = self._checked
        height = max(self.view_height, 540)
        p = K.Painter(width, height, scale)
        light = K.radial_light(p.px(width), p.px(height), p.px(width * 0.22), p.px(-height * 0.12),
                               p.px(width * 0.7), p.px(height * 0.7), LIGHT)
        p.img.paste(light, (0, 0), light)
        regions: list[K.Region] = []
        x, y, w = 34, 30, width - 68
        p.text(x, y, t("welcome_title"), TITLE, max_w=w)
        y += 38 + 8
        y += p.paragraph(x, y, t("welcome_lead"), LEAD, w) + 18
        left_w = w - 290 - 20
        ly = y
        rows = [(discord, "check_discord"), (guitar_rig, "check_gr"), (ocr, "check_ocr")]
        for i, (ok, key) in enumerate(rows):
            if i:
                p.hline(x, x + left_w, ly, K.PANEL_LINE)
                ly += 9
            p.circle(x + 11, ly + 11, 11, OK_BG if ok else WARN_BG)
            if ok:
                p.icon("check", x + 5, ly + 5, 12, K.GREEN, stroke=2.6)
            else:
                p.circle(x + 11, ly + 11, 3.5, K.AMBER)
            suffix = "ok" if ok else "no"
            p.text(x + 34, ly + 1, t(f"{key}_{suffix}"), CHECK, max_w=left_w - 34)
            ly += 2 + 13.5 * 1.3
            ly += p.paragraph(x + 34, ly, t(f"{key}_{suffix}_hint"), CHECK_HINT, left_w - 34) + 9
        p.hline(x, x + left_w, ly, K.PANEL_LINE)
        ly += 6 + 11
        p.text(x, ly, t("welcome_goal"), LABEL)
        ly += 13.5 * 1.3 + 8
        goal = self._goal()
        labels = [t("goal_none") if g == 0 else f"{g} min" for g in GOALS]
        selected = GOALS.index(goal) if goal in GOALS else -1
        seg_w = sum(p.measure(lbl, K.Style(12.5, 600)) + 24 for lbl in labels) + 2 * 3 + 8
        _w, seg_h, segs = K.segmented(p, x + seg_w, ly, labels, selected, [str(g) for g in GOALS],
                                      [lambda g=g: self._set_goal(g) for g in GOALS])
        regions.extend(segs)
        ly += seg_h + 11
        p.hline(x, x + left_w, ly, K.PANEL_LINE)
        ly += 11
        p.text(x, ly + (22 - 13.5 * 1.3) / 2, t("set_autostart"), LABEL)
        K.switch(p, x + left_w - 38, ly, self._autostart_on())
        regions.append(K.Region(x + left_w - 42, ly - 6, x + left_w + 4, ly + 28, self._toggle_autostart, "autostart"))

        rx = x + left_w + 20
        ry = y + p.paragraph(rx, y, t("welcome_preview"), PREVIEW, 290) + 10
        K.discord_card(p, rx, ry, 290, t("verb_playing"), self._sample(t), [])

        foot = height - 26 - 38
        p.text(x, foot + (38 - 13 * 1.3) / 2, t("welcome_later"), FOOT, max_w=w - 160)
        bw = p.measure(t("welcome_start"), PRIMARY) + 36
        bx = x + w - bw
        p.rrect(bx, foot, bw, 38, 11, K.gradient(p.px(bw), p.px(38), K.AMBER, K.ORANGE, horizontal=True))
        p.text(bx + 18, foot + (38 - 13.5 * 1.3) / 2, t("welcome_start"), PRIMARY)
        regions.append(K.Region(bx, foot, bx + bw, foot + 38, self.on_start, "start"))
        return K.Rendered(p.img, height, regions)
