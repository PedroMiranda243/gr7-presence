"""A janela principal do GR7 Presence (direção "Palco"): a barra lateral e a página escolhida.

Uma janela só, com uma página para cada assunto, em vez de uma janela para cada coisa. Cada página se
desenha numa imagem do Pillow (`ui_kit`); aqui fica só o Tkinter: a rolagem, os cliques, a
atualização a cada 10 segundos e a barra de título escura.
"""
from __future__ import annotations

import ctypes
import logging
import tkinter as tk
from typing import Callable

from PIL import ImageTk

from . import ui_kit as K
from .app_icon import PNG as LOGO
from .i18n import Translator

log = logging.getLogger(__name__)

SIZE = (960, 640)          # pixels lógicos, como nos exemplos aprovados
MIN_SIZE = (860, 560)
RAIL_W = 78
ITEM_H = 10 + 20 + 6 + 10.5 + 8
REFRESH_MS = 10_000
WHEEL_STEP = 60            # pixels lógicos por clique da roda do mouse
RAIL_LABEL = K.Style(10.5, 600, K.ICON_OFF, line=1.0)
TITLE_TEXT = "#B9BDC8"


def _colorref(color: str) -> ctypes.c_int:
    r, g, b = K._rgb(color)
    return ctypes.c_int(r | g << 8 | b << 16)


def dark_title_bar(win: tk.Misc) -> None:
    """Barra de título escura (Windows 10 e 11), na cor do palco no Windows 11. Se falhar, fica a padrão."""
    try:
        hwnd = int(win.wm_frame(), 16)
        dwm = ctypes.windll.dwmapi
        on = ctypes.c_int(1)
        for attr in (20, 19):   # DWMWA_USE_IMMERSIVE_DARK_MODE; o 19 é o das versões antigas do Windows 10
            if dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(on), ctypes.sizeof(on)) == 0:
                break
        for attr, color in ((35, K.BG), (36, TITLE_TEXT)):   # DWMWA_CAPTION_COLOR, DWMWA_TEXT_COLOR (só no 11)
            value = _colorref(color)
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
    except (AttributeError, OSError, ValueError, tk.TclError) as exc:
        log.debug("Barra de título padrão: %s", exc)


def render_rail(height: float, scale: float, pages: list, selected: str, hover: str | None,
                update_label: str | None, t: Translator) -> K.Rendered:
    """A barra lateral: o ícone, uma entrada por página e, embaixo, a versão nova quando houver."""
    p = K.Painter(RAIL_W, height, scale, K.RAIL)
    p.rect(RAIL_W - 1, 0, 1, height, K.RAIL_LINE)
    p.picture(LOGO, 22, 12, 34)
    regions = []
    y = 12 + 34 + 10
    for page in pages:
        on = page.key == selected
        if on or page.key == hover:
            p.rrect(7, y, 64, ITEM_H, 12, K.RAIL_ON if on else "#151821")
        color = K.TEXT if on else K.ICON_OFF
        p.icon(page.icon, 29, y + 10, 20, K.AMBER if on else K.ICON_OFF)
        p.text(39, y + 36, t(page.label_key), RAIL_LABEL, anchor="m", color=color)
        regions.append(K.Region(7, y, 71, y + ITEM_H, page.key, page.key))
        y += ITEM_H + 6
    if update_label:
        uy = height - 14 - ITEM_H
        if hover == "update":
            p.rrect(7, uy, 64, ITEM_H, 12, "#151821")
        p.icon("up", 29, uy + 10, 20, K.AMBER)
        p.text(39, uy + 36, update_label, RAIL_LABEL, anchor="m", color=K.AMBER)
        p.circle(7 + 64 - 16 - 3.5, uy + 8 + 3.5, 3.5, K.ORANGE)
        regions.append(K.Region(7, uy, 71, uy + ITEM_H, "update", "update"))
    return K.Rendered(p.img, height, regions)


class MainWindow:
    def __init__(self, master: tk.Misc, pages: list, translator: Callable[[], Translator],
                 update_version: Callable[[], str | None], on_update: Callable[[], None], page: str | None = None):
        self.pages = pages
        self.by_key = {p.key: p for p in pages}
        self.translator = translator
        self.update_version = update_version
        self.on_update = on_update
        self.current = page if page in self.by_key else pages[0].key
        self.alive = True
        self.hover: str | None = None
        self._page: K.Rendered | None = None
        self._rail: K.Rendered | None = None
        self._photos: dict[str, ImageTk.PhotoImage] = {}
        self._thumb_h = 0
        self._resize_job: str | None = None
        self._refresh_job: str | None = None
        for p in pages:
            p.on_change = self.render_page

        self.win = tk.Toplevel(master)
        self.win.title("GR7 Presence")
        self.win.configure(bg=K.BG)
        # O programa é DPI aware: o desenho é feito em pixels de tela, na escala do Windows.
        self.scale = s = max(1.0, self.win.winfo_fpixels("1i") / 96)
        self.win.geometry(f"{round(SIZE[0] * s)}x{round(SIZE[1] * s)}")
        self.win.minsize(round(MIN_SIZE[0] * s), round(MIN_SIZE[1] * s))
        self.win.protocol("WM_DELETE_WINDOW", self.close)   # o ícone vem do iconbitmap(default=) da bandeja

        self.rail = tk.Canvas(self.win, width=round(RAIL_W * s), bg=K.RAIL, highlightthickness=0, bd=0)
        self.rail.pack(side="left", fill="y")
        self.view = tk.Canvas(self.win, bg=K.BG, highlightthickness=0, bd=0, yscrollincrement=1)
        self.view.pack(side="left", fill="both", expand=True)
        self._rail_item = self.rail.create_image(0, 0, anchor="nw")
        self._page_item = self.view.create_image(0, 0, anchor="nw")
        self._thumb_item = self.view.create_image(0, 0, anchor="ne", state="hidden")

        self.rail.bind("<Configure>", lambda _e: self.render_rail())
        self.rail.bind("<Motion>", self._rail_motion)
        self.rail.bind("<Leave>", lambda _e: self._set_hover(None))
        self.rail.bind("<Button-1>", self._rail_click)
        self.view.bind("<Configure>", self._view_resized)
        self.view.bind("<Motion>", self._view_motion)
        self.view.bind("<Button-1>", self._view_click)
        self.win.bind("<MouseWheel>", self._wheel)
        self.win.after_idle(lambda: dark_title_bar(self.win))
        self._refresh_job = self.win.after(REFRESH_MS, self._refresh)
        self.focus()

    # ---- abrir, trocar de página, fechar ----------------------------------------------------
    def show(self, page: str) -> None:
        if page in self.by_key and page != self.current:
            self.current = page
            self.view.yview_moveto(0)
            self.render_page()
            self.render_rail()
        self.focus()

    def focus(self) -> None:
        self.win.deiconify()
        self.win.lift()
        self.win.attributes("-topmost", True)   # aberta pela bandeja, tende a nascer atrás das outras
        self.win.after(500, lambda: self.alive and self.win.attributes("-topmost", False))
        self.win.focus_force()

    def close(self) -> None:
        self.alive = False
        for job in (self._resize_job, self._refresh_job):
            if job:
                self.win.after_cancel(job)
        self.win.destroy()

    # ---- desenho ------------------------------------------------------------------------------
    def render_page(self) -> None:
        if not self.alive:
            return
        width = self.view.winfo_width()
        if width <= 1:
            return
        page = self.by_key[self.current]
        try:
            rendered = page.render(width / self.scale, self.scale, self.translator())
        except Exception:   # uma página com defeito não pode derrubar a bandeja
            log.exception("Não consegui desenhar a página %s", self.current)
            return
        self._page = rendered
        self._photos["page"] = ImageTk.PhotoImage(rendered.image)
        self.view.itemconfigure(self._page_item, image=self._photos["page"])
        self.view.configure(scrollregion=(0, 0, rendered.image.width, rendered.image.height))
        self._update_thumb()

    def render_rail(self) -> None:
        if not self.alive:
            return
        height = self.rail.winfo_height()
        if height <= 1:
            return
        try:
            self._rail = render_rail(height / self.scale, self.scale, self.pages, self.current, self.hover,
                                     self.update_version(), self.translator())
        except Exception:
            log.exception("Não consegui desenhar a barra lateral")
            return
        self._photos["rail"] = ImageTk.PhotoImage(self._rail.image)
        self.rail.itemconfigure(self._rail_item, image=self._photos["rail"])

    def _update_thumb(self) -> None:
        """Barra de rolagem fina, só quando a página não cabe na janela."""
        top, bottom = self.view.yview()
        if not self._page or bottom - top >= 1:
            self.view.itemconfigure(self._thumb_item, state="hidden")
            return
        view_h = self.view.winfo_height()
        thumb_h = max(round(30 * self.scale), round((bottom - top) * view_h))
        if thumb_h != self._thumb_h:
            p = K.Painter(4, thumb_h / self.scale, self.scale, K.BG)
            p.rrect(0, 0, 4, thumb_h / self.scale, 2, K.SCROLL_THUMB)
            self._photos["thumb"] = ImageTk.PhotoImage(p.img)
            self.view.itemconfigure(self._thumb_item, image=self._photos["thumb"])
            self._thumb_h = thumb_h
        y = self.view.canvasy(0) + top * (view_h - thumb_h) / max(1e-6, 1 - (bottom - top))
        self.view.coords(self._thumb_item, self.view.winfo_width() - round(3 * self.scale), y)
        self.view.itemconfigure(self._thumb_item, state="normal")

    # ---- eventos ------------------------------------------------------------------------------
    def _view_resized(self, _event) -> None:
        if self._resize_job:
            self.win.after_cancel(self._resize_job)
        self._resize_job = self.win.after(60, self.render_page)

    def _refresh(self) -> None:
        if not self.alive:
            return
        if self.win.state() != "iconic":   # minimizada, ninguém está vendo
            self.render_page()
            self.render_rail()
        self._refresh_job = self.win.after(REFRESH_MS, self._refresh)

    def _wheel(self, event) -> None:
        self.view.yview_scroll(int(-event.delta / 120 * WHEEL_STEP * self.scale), "units")
        self._update_thumb()

    def _page_region(self, event) -> K.Region | None:
        if not self._page:
            return None
        x = self.view.canvasx(event.x) / self.scale
        y = self.view.canvasy(event.y) / self.scale
        return next((r for r in self._page.regions if r.hit(x, y)), None)

    def _view_motion(self, event) -> None:
        self.view.configure(cursor="hand2" if self._page_region(event) else "")

    def _view_click(self, event) -> None:
        region = self._page_region(event)
        if region:
            region.action()

    def _rail_region(self, event) -> K.Region | None:
        if not self._rail:
            return None
        return next((r for r in self._rail.regions if r.hit(event.x / self.scale, event.y / self.scale)), None)

    def _set_hover(self, key: str | None) -> None:
        if key != self.hover:
            self.hover = key
            self.render_rail()

    def _rail_motion(self, event) -> None:
        region = self._rail_region(event)
        self.rail.configure(cursor="hand2" if region else "")
        self._set_hover(region.key if region else None)

    def _rail_click(self, event) -> None:
        region = self._rail_region(event)
        if not region:
            return
        if region.key == "update":
            self.on_update()
        else:
            self.show(region.key)
