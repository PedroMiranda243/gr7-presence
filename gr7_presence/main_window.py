"""A janela principal do GR7 Presence (direção "Palco"): a barra lateral e a página escolhida.

Uma janela só, com uma página para cada assunto, em vez de uma janela para cada coisa. Cada página se
desenha numa imagem do Pillow (`ui_kit`); aqui fica só o Tkinter: a rolagem, os cliques e o arrastar,
os campos de texto (tk.Entry por cima do desenho), as listas de opções, a atualização a cada
10 segundos e a barra de título escura.

Uma página tem `key`, `icon`, `label_key` e `render(largura, escala, t)`. Opcionalmente, `side_width` e
`render_side(...)` para um painel fixo à direita (a prévia dos Ajustes), `focus_field(chave)`,
`end_drag()` e `on_show()`, chamado quando a página aparece (a Conquistas marca as novas como vistas).
A janela dá à página `on_change` (pede para redesenhar) e `host` (esta janela).
"""
from __future__ import annotations

import ctypes
import logging
import tkinter as tk
import tkinter.font as tkfont
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
MENU_ITEM_H = 32
TRANSPARENT = "#010203"    # cor que o Windows deixa transparente na lista de opções (cantos redondos)


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
        for attr, color in ((35, K.BG), (36, K.TITLE_TEXT)):   # DWMWA_CAPTION_COLOR, DWMWA_TEXT_COLOR (só no 11)
            value = _colorref(color)
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
    except (AttributeError, OSError, ValueError, tk.TclError) as exc:
        log.debug("Barra de título padrão: %s", exc)


def render_rail(height: float, scale: float, pages: list, selected: str, hover: str | None,
                update_label: str | None, t: Translator) -> K.Rendered:
    """A barra lateral: o ícone, uma entrada por página e, embaixo, a versão nova quando houver.
    Páginas com `rail = False` (a de atualização) não ganham entrada própria."""
    pages = [page for page in pages if getattr(page, "rail", True)]
    p = K.Painter(RAIL_W, height, scale, K.RAIL)
    p.rect(RAIL_W - 1, 0, 1, height, K.RAIL_LINE)
    p.picture(LOGO, 22, 12, 34)
    regions = []
    y = 12 + 34 + 10
    for page in pages:
        on = page.key == selected
        if on or page.key == hover:
            p.rrect(7, y, 64, ITEM_H, 12, K.RAIL_ON if on else K.FIELD)
        color = K.TEXT if on else K.ICON_OFF
        p.icon(page.icon, 29, y + 10, 20, K.AMBER if on else K.ICON_OFF)
        p.text(39, y + 36, t(page.label_key), RAIL_LABEL, anchor="m", color=color)
        regions.append(K.Region(7, y, 71, y + ITEM_H, page.key, page.key, radius=12))
        y += ITEM_H + 6
    if update_label:
        uy = height - 14 - ITEM_H
        if selected == "update" or hover == "update":
            p.rrect(7, uy, 64, ITEM_H, 12, K.RAIL_ON if selected == "update" else K.FIELD)
        p.icon("up", 29, uy + 10, 20, K.AMBER)
        p.text(39, uy + 36, update_label, RAIL_LABEL, anchor="m", color=K.AMBER)
        p.circle(7 + 64 - 16 - 3.5, uy + 8 + 3.5, 3.5, K.ORANGE)
        regions.append(K.Region(7, uy, 71, uy + ITEM_H, "update", "update", radius=12))
    return K.Rendered(p.img, height, regions)


def render_menu(width: float, options: list[tuple[object, str]], current: object, hover: int | None,
                scale: float) -> K.Rendered:
    """A lista de opções de um campo de escolha."""
    h = 8 + MENU_ITEM_H * len(options)
    p = K.Painter(width, h, scale, TRANSPARENT)
    p.rrect(0, 0, width, h, 10, K.FIELD, outline=K.FIELD_LINE)
    regions = []
    for i, (value, label) in enumerate(options):
        y = 4 + i * MENU_ITEM_H
        if i == hover:
            p.rrect(4, y, width - 8, MENU_ITEM_H, 6, K.SELECTED)
        p.text(14, y + (MENU_ITEM_H - K.CONTROL.size * K.CONTROL.line) / 2, label, K.CONTROL, max_w=width - 48)
        if value == current:
            p.icon("check", width - 14 - 16, y + 8, 16, K.AMBER, stroke=2.4)
        regions.append(K.Region(0, y, width, y + MENU_ITEM_H, value, str(i)))
    return K.Rendered(p.img, h, regions)


class _Entry:
    """Um tk.Entry com o texto de exemplo (placeholder) que o Tkinter não tem."""

    def __init__(self, window: "MainWindow", spec: K.Field):
        self.window = window
        self.key = spec.key
        self.placeholder = spec.placeholder
        self.on_change = spec.on_change
        self.showing_placeholder = False
        self.var = tk.StringVar(value=spec.value)
        check = (window.win.register(lambda text: self.showing_placeholder or len(text) <= spec.max_len), "%P")
        self.widget = tk.Entry(window.view, textvariable=self.var, font=window.entry_font, bg=K.FIELD, fg=K.TEXT,
                               insertbackground=K.TEXT, relief="flat", bd=0, highlightthickness=0,
                               disabledbackground=K.FIELD, selectbackground=K.SELECTION, selectforeground=K.TEXT,
                               validate="key", validatecommand=check)
        self.item = window.view.create_window(0, 0, anchor="w", window=self.widget)
        self.widget.bind("<FocusIn>", self._focus_in)
        self.widget.bind("<FocusOut>", self._focus_out)
        self.widget.bind("<Return>", lambda _e: window.view.focus_set())
        self.var.trace_add("write", self._changed)
        if not spec.value:
            self._show_placeholder()

    def _show_placeholder(self) -> None:
        if self.placeholder:
            self.showing_placeholder = True
            self.var.set(self.placeholder)
            self.widget.configure(fg=K.FAINT)

    def _focus_in(self, _event) -> None:
        if self.showing_placeholder:
            self.var.set("")
            self.showing_placeholder = False
            self.widget.configure(fg=K.TEXT)
        self.window.field_focus(self.key)

    def _focus_out(self, _event) -> None:
        if not self.var.get():
            self._show_placeholder()
        self.window.field_focus(None)

    def _changed(self, *_args) -> None:
        if not self.showing_placeholder and self.on_change:
            self.on_change(self.var.get())

    def destroy(self) -> None:
        self.window.view.delete(self.item)
        self.widget.destroy()


class MainWindow:
    def __init__(self, master: tk.Misc, pages: list, translator: Callable[[], Translator],
                 update_version: Callable[[], str | None], on_update: Callable[[], None] | None = None,
                 page: str | None = None, size: tuple[int, int] = SIZE, min_size: tuple[int, int] = MIN_SIZE,
                 rail: bool = True, on_close: Callable[[], None] | None = None):
        self.on_close = on_close
        self.pages = pages
        self.by_key = {p.key: p for p in pages}
        self.translator = translator
        self.update_version = update_version
        self.on_update = on_update
        self.current = page if page in self.by_key else pages[0].key
        self.alive = True
        self.hover: str | None = None
        self._page: K.Rendered | None = None
        self._side: K.Rendered | None = None
        self._rail: K.Rendered | None = None
        self._photos: dict[str, ImageTk.PhotoImage] = {}
        self._entries: dict[str, _Entry] = {}
        self._drag: K.Region | None = None
        self._menu: tk.Toplevel | None = None
        self._menu_at = ""                          # posição e tamanho da janela quando a lista abriu
        self._thumb_h = 0
        self._jobs: dict[str, str] = {}
        self._kb: tuple[str, str] | None = None   # controle com o foco do teclado: (área, chave)
        for p in pages:
            p.on_change = self.request_render
            p.host = self

        self.win = tk.Toplevel(master)
        self.win.title("GR7 Presence")
        self.win.configure(bg=K.BG)
        # O programa é DPI aware: o desenho é feito em pixels de tela, na escala do Windows.
        self.scale = s = max(1.0, self.win.winfo_fpixels("1i") / 96)
        self.win.geometry(f"{round(size[0] * s)}x{round(size[1] * s)}")
        self.win.minsize(round(min_size[0] * s), round(min_size[1] * s))
        self.win.protocol("WM_DELETE_WINDOW", self.close)   # o ícone vem do iconbitmap(default=) da bandeja
        families = set(tkfont.families(self.win))
        family = "Segoe UI Variable Text" if "Segoe UI Variable Text" in families else "Segoe UI"
        self.entry_font = tkfont.Font(self.win, family=family, size=-round(13.5 * s))

        self.rail = tk.Canvas(self.win, width=round(RAIL_W * s), bg=K.RAIL, highlightthickness=0, bd=0)
        if rail:
            self.rail.pack(side="left", fill="y")
        self.view = tk.Canvas(self.win, bg=K.BG, highlightthickness=0, bd=0, yscrollincrement=1, takefocus=1)
        self.view.pack(side="left", fill="both", expand=True)
        self.side = tk.Canvas(self.win, width=1, bg=K.BG, highlightthickness=0, bd=0)
        self._rail_item = self.rail.create_image(0, 0, anchor="nw")
        self._page_item = self.view.create_image(0, 0, anchor="nw")
        self._thumb_item = self.view.create_image(0, 0, anchor="ne", state="hidden")
        self._side_item = self.side.create_image(0, 0, anchor="nw")

        self.rail.bind("<Configure>", lambda _e: self.render_rail())
        self.rail.bind("<Motion>", self._rail_motion)
        self.rail.bind("<Leave>", lambda _e: self._set_hover(None))
        self.rail.bind("<Button-1>", self._rail_click)
        self.view.bind("<Configure>", lambda _e: self.request_render(60))
        self.view.bind("<Motion>", self._view_motion)
        self.view.bind("<Button-1>", self._view_press)
        self.view.bind("<B1-Motion>", self._view_drag)
        self.view.bind("<ButtonRelease-1>", self._view_release)
        self.side.bind("<Configure>", lambda _e: self.request_render(60))
        self.side.bind("<Motion>", self._side_motion)
        self.side.bind("<Button-1>", self._side_click)
        self.win.bind("<MouseWheel>", self._wheel)
        self.win.bind("<Configure>", self._window_moved, add="+")
        self.win.bind("<Unmap>", self._window_moved, add="+")
        # Teclado: Tab e Shift+Tab andam pelos controles, Enter ou espaço acionam, setas mexem no deslizante.
        self.win.bind("<Tab>", lambda _e: self._tab(1))
        self.win.bind("<Shift-Tab>", lambda _e: self._tab(-1))
        for canvas in (self.rail, self.view, self.side):
            canvas.configure(takefocus=1)
            canvas.bind("<Return>", self._activate)
            canvas.bind("<space>", self._activate)
            canvas.bind("<Left>", lambda _e: self._arrow(-1))
            canvas.bind("<Right>", lambda _e: self._arrow(1))
        self._jobs["title"] = self.win.after_idle(lambda: dark_title_bar(self.win))
        self._layout_side()
        self._jobs["refresh"] = self.win.after(self._refresh_ms(), self._refresh)
        self._shown()
        self.focus()

    # ---- abrir, trocar de página, fechar ----------------------------------------------------
    @property
    def page(self):
        return self.by_key[self.current]

    def show(self, page: str) -> None:
        if page in self.by_key and page != self.current:
            self.close_menu()
            self.view.focus_set()
            self._kb = None
            self.current = page
            self.view.yview_moveto(0)
            self._layout_side()
            self._shown()
            self.render_page()
            self.render_rail()
        self.focus()

    def _shown(self) -> None:
        hook = getattr(self.page, "on_show", None)
        if hook:
            try:
                hook()
            except Exception:   # um defeito aqui não pode impedir a página de abrir
                log.exception("Falha ao abrir a página %s", self.current)

    def focus(self) -> None:
        self.win.deiconify()
        self.win.lift()
        self.win.attributes("-topmost", True)   # aberta pela bandeja, tende a nascer atrás das outras
        self.later(500, lambda: self.win.attributes("-topmost", False), key="topmost")
        self.win.focus_force()

    def close(self) -> None:
        self.alive = False
        self.close_menu()
        for job in self._jobs.values():
            self.win.after_cancel(job)
        self._jobs.clear()
        self.win.destroy()
        if self.on_close:
            self.on_close()

    def later(self, ms: int, fn: Callable[[], None], key: str | None = None) -> None:
        """Agenda `fn` na thread da interface; com `key`, o pedido anterior igual é cancelado."""
        if not self.alive:
            return
        if key and key in self._jobs:
            self.win.after_cancel(self._jobs.pop(key))

        def run():
            if key:
                self._jobs.pop(key, None)
            if self.alive:
                fn()
        job = self.win.after(ms, run)
        if key:
            self._jobs[key] = job

    # ---- desenho ------------------------------------------------------------------------------
    def request_render(self, delay: int = 15) -> None:
        """Junta vários pedidos seguidos (digitar, arrastar) num desenho só."""
        if "render" not in self._jobs:
            self.later(delay, self._render_now, "render")

    def _render_now(self) -> None:
        self.render_page()
        self.render_side()
        self.render_rail()   # o idioma pode ter mudado nos Ajustes

    def _layout_side(self) -> None:
        width = getattr(self.page, "side_width", 0)
        if width:
            self.side.configure(width=round(width * self.scale))
            self.side.pack(side="right", fill="y", before=self.view)
        else:
            self.side.pack_forget()
            self._side = None

    def render_page(self) -> None:
        if not self.alive:
            return
        width = self.view.winfo_width()
        if width <= 1:
            return
        self.page.view_height = self.view.winfo_height() / self.scale   # quem ocupa a altura toda usa
        try:
            rendered = self.page.render(width / self.scale, self.scale, self.translator())
        except Exception:   # uma página com defeito não pode derrubar a bandeja
            log.exception("Não consegui desenhar a página %s", self.current)
            return
        self._page = rendered
        self._photos["page"] = ImageTk.PhotoImage(rendered.image)
        self.view.itemconfigure(self._page_item, image=self._photos["page"])
        self.view.configure(scrollregion=(0, 0, rendered.image.width, rendered.image.height))
        self._sync_fields(rendered.fields)
        self._update_thumb()
        self._draw_ring()

    def render_side(self) -> None:
        if not self.alive or not getattr(self.page, "side_width", 0):
            return
        width, height = self.side.winfo_width(), self.side.winfo_height()
        if width <= 1 or height <= 1:
            return
        try:
            self._side = self.page.render_side(width / self.scale, height / self.scale, self.scale, self.translator())
        except Exception:
            log.exception("Não consegui desenhar o painel lateral de %s", self.current)
            return
        self._photos["side"] = ImageTk.PhotoImage(self._side.image)
        self.side.itemconfigure(self._side_item, image=self._photos["side"])
        self._draw_ring()

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
        self._draw_ring()

    def _sync_fields(self, fields: list[K.Field]) -> None:
        """Põe, move e tira os tk.Entry conforme os campos que a página desenhou."""
        keep = set()
        for spec in fields:
            keep.add(spec.key)
            entry = self._entries.get(spec.key) or self._entries.setdefault(spec.key, _Entry(self, spec))
            entry.on_change = spec.on_change
            self.view.coords(entry.item, (spec.x + 12) * self.scale, (spec.y + spec.h / 2) * self.scale)
            self.view.itemconfigure(entry.item, width=round((spec.w - 24) * self.scale))
        for key in [k for k in self._entries if k not in keep]:
            self._entries.pop(key).destroy()

    def field_focus(self, key: str | None) -> None:
        handler = getattr(self.page, "focus_field", None)
        if handler:
            handler(key)

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

    # ---- lista de opções -----------------------------------------------------------------------
    def open_menu(self, x: float, y: float, width: float, options: list[tuple[object, str]], current: object,
                  on_pick: Callable[[object], None], above: float | None = None, zoom: float = 1.0) -> None:
        """Abre a lista de opções logo abaixo de um campo (`x`, `y` em pixels lógicos da página). Se ela
        passar do pé da janela, abre acima, terminando em `above` (o topo do campo, menos a folga).
        Setas para cima e para baixo escolhem, Enter confirma, Esc fecha. Com `zoom` (o Painel ampliado
        em tela cheia), a lista é desenhada maior na mesma proporção; `width` continua a da lista normal."""
        self.close_menu()
        s = self.scale * zoom     # a escala do desenho da lista
        menu = tk.Toplevel(self.win)
        menu.overrideredirect(True)
        try:
            menu.attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass
        canvas = tk.Canvas(menu, bg=TRANSPARENT, highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)
        item = canvas.create_image(0, 0, anchor="nw")
        state = {"hover": None, "rendered": None}

        def draw():
            state["rendered"] = render_menu(width, options, current, state["hover"], s)
            self._photos["menu"] = ImageTk.PhotoImage(state["rendered"].image)
            canvas.itemconfigure(item, image=self._photos["menu"])

        def region(event):
            # Pelas coordenadas de tela: o clique fora da lista chega a ela pelo grab, com o x e o y
            # do evento sem valor.
            x, y = event.x_root - canvas.winfo_rootx(), event.y_root - canvas.winfo_rooty()
            inside = 0 <= x < canvas.winfo_width() and 0 <= y < canvas.winfo_height()
            hit = [r for r in state["rendered"].regions if r.hit(x / s, y / s)] if inside else []
            return hit[0] if hit else None

        def motion(event):
            r = region(event)
            hover = int(r.key) if r else None
            if hover != state["hover"]:
                state["hover"] = hover
                draw()

        def click(event):
            r = region(event) if event.num == 1 else None   # fora da lista, ou outro botão: só fecha
            self.close_menu()
            if r is not None:
                on_pick(r.action)

        def move(step):
            values = [v for v, _ in options]
            start = state["hover"] if state["hover"] is not None else (values.index(current) if current in values else -1)
            state["hover"] = (start + step) % len(options)
            draw()

        def choose(_event=None):
            hover = state["hover"]
            self.close_menu()
            if hover is not None:
                on_pick(options[hover][0])

        draw()
        img = state["rendered"].image
        sx = self.view.winfo_rootx() + round(x * self.scale - self.view.canvasx(0))
        sy = self.view.winfo_rooty() + round(y * self.scale - self.view.canvasy(0))
        bottom = self.win.winfo_rooty() + self.win.winfo_height()
        if above is not None and sy + img.height > bottom:   # não cabe embaixo: abre para cima
            sy = self.view.winfo_rooty() + round(above * self.scale - self.view.canvasy(0)) - img.height
        menu.geometry(f"{img.width}x{img.height}+{sx}+{sy}")
        canvas.bind("<Motion>", motion)
        # Na janela da lista, não no desenho: com o grab, o clique em qualquer ponto da janela do programa
        # chega à janela da lista, e o clique fora fecha sem chegar ao que estava embaixo.
        menu.bind("<ButtonPress>", click)
        menu.bind("<Escape>", lambda _e: self.close_menu())
        menu.bind("<Down>", lambda _e: move(1))
        menu.bind("<Up>", lambda _e: move(-1))
        menu.bind("<Return>", choose)
        menu.bind("<space>", choose)
        menu.bind("<FocusOut>", lambda _e: self.close_menu())   # outro programa veio para a frente
        self._menu = menu
        self._menu_at = self.win.winfo_geometry()
        menu.focus_force()
        try:
            menu.grab_set()   # clique fora da lista chega aqui e fecha a lista
        except tk.TclError:
            pass

    def close_menu(self) -> None:
        if self._menu is not None:
            menu, self._menu = self._menu, None
            try:
                menu.grab_release()
                menu.destroy()
            except tk.TclError:
                pass
            if self.alive:
                self.field_focus(None)   # o campo de escolha perde a borda âmbar quando a lista fecha

    def _window_moved(self, event) -> None:
        """Arrastar a janela pela barra de título, mudar o tamanho ou minimizar também é clicar fora. A
        lista é uma janela à parte e ficaria solta na tela, longe do campo."""
        if self._menu is None or event.widget is not self.win:
            return
        if event.type == tk.EventType.Unmap or self.win.winfo_geometry() != self._menu_at:
            self.close_menu()

    # ---- eventos ------------------------------------------------------------------------------
    def _refresh(self) -> None:
        if not self.alive:
            return
        if self.win.state() != "iconic" and not self._drag:   # minimizada, ninguém está vendo
            self.render_page()
            self.render_side()
            self.render_rail()
        self._jobs["refresh"] = self.win.after(self._refresh_ms(), self._refresh)

    def _refresh_ms(self) -> int:
        """O Painel conta os segundos do cartão; as outras páginas mudam devagar."""
        return getattr(self.page, "refresh_ms", REFRESH_MS)

    def _wheel(self, event) -> None:
        self.view.yview_scroll(int(-event.delta / 120 * WHEEL_STEP * self.scale), "units")
        self._update_thumb()

    def _page_point(self, event) -> tuple[float, float]:
        return self.view.canvasx(event.x) / self.scale, self.view.canvasy(event.y) / self.scale

    def _page_region(self, event) -> K.Region | None:
        if not self._page:
            return None
        x, y = self._page_point(event)
        return next((r for r in self._page.regions if r.hit(x, y)), None)

    def _view_motion(self, event) -> None:
        self.view.configure(cursor="hand2" if self._page_region(event) else "")

    def _view_press(self, event) -> None:
        self.view.focus_set()   # clicar fora de um campo de texto tira o foco dele
        self._kb = None         # com o mouse, o contorno do teclado some
        self._draw_ring()
        region = self._page_region(event)
        if not region:
            return
        if region.drag:
            self._drag = region
            region.drag(*self._page_point(event))
        else:
            region.action()

    def _view_drag(self, event) -> None:
        if self._drag:
            self._drag.drag(*self._page_point(event))

    def _view_release(self, _event) -> None:
        if self._drag:
            self._drag = None
            done = getattr(self.page, "end_drag", None)
            if done:
                done()

    def _side_region(self, event) -> K.Region | None:
        if not self._side:
            return None
        return next((r for r in self._side.regions if r.hit(event.x / self.scale, event.y / self.scale)), None)

    def _side_motion(self, event) -> None:
        self.side.configure(cursor="hand2" if self._side_region(event) else "")

    def _side_click(self, event) -> None:
        self._kb = None
        self._draw_ring()
        region = self._side_region(event)
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
        self._kb = None
        self._draw_ring()
        region = self._rail_region(event)
        if not region:
            return
        self._rail_action(region)

    def _rail_action(self, region: K.Region) -> None:
        if region.key == "update" and "update" not in self.by_key:
            if self.on_update:
                self.on_update()
        else:
            self.show(region.key)

    # ---- teclado ------------------------------------------------------------------------------
    def _targets(self) -> list[tuple[str, str]]:
        """Os controles na ordem do Tab: barra lateral, página (áreas e campos, de cima para baixo) e
        o painel da direita."""
        order: list[tuple[str, str]] = []
        if self._rail and self.rail.winfo_ismapped():
            order += [("rail", r.key) for r in sorted(self._rail.regions, key=lambda r: (r.y0, r.x0))]
        if self._page:
            items = [((r.y0, r.x0), ("page", r.key)) for r in self._page.regions]
            items += [((f.y, f.x), ("entry", f.key)) for f in self._page.fields]
            order += [target for _pos, target in sorted(items, key=lambda i: i[0])]
        if self._side and getattr(self.page, "side_width", 0):
            order += [("side", r.key) for r in sorted(self._side.regions, key=lambda r: (r.y0, r.x0))]
        return order

    def _tab(self, step: int) -> str:
        targets = self._targets()
        if not targets:
            return "break"
        focused = self.win.focus_get()
        current = next((("entry", k) for k, e in self._entries.items() if e.widget is focused), None) or self._kb
        if current in targets:
            index = (targets.index(current) + step) % len(targets)
        else:
            index = 0 if step > 0 else len(targets) - 1
        self._focus_target(targets[index])
        return "break"

    def _focus_target(self, target: tuple[str, str]) -> None:
        area, key = target
        if area == "entry":
            self._kb = None
            self._draw_ring()
            self._entries[key].widget.focus_set()
            return
        self._kb = target
        {"rail": self.rail, "side": self.side}.get(area, self.view).focus_set()
        region = self._region_of(target)
        if area == "page" and region and self._page:   # rola até o controle, se ele estiver fora da vista
            top, view_h = self.view.canvasy(0), self.view.winfo_height()
            if region.y0 * self.scale < top or region.y1 * self.scale > top + view_h:
                self.view.yview_moveto(max(0.0, (region.y0 - 20) * self.scale / max(1, self._page.image.height)))
                self._update_thumb()
        self._draw_ring()

    def _region_of(self, target: tuple[str, str] | None) -> K.Region | None:
        if not target:
            return None
        rendered = {"rail": self._rail, "page": self._page, "side": self._side}.get(target[0])
        return next((r for r in rendered.regions if r.key == target[1]), None) if rendered else None

    def _draw_ring(self) -> None:
        """O contorno âmbar no controle que tem o foco do teclado (o mesmo âmbar do campo com foco)."""
        for canvas in (self.rail, self.view, self.side):
            canvas.delete("kbring")
        region = self._region_of(self._kb)
        if not region:
            return
        canvas = {"rail": self.rail, "side": self.side}.get(self._kb[0], self.view)
        s = self.scale
        x0, y0 = round((region.x0 - 3) * s), round((region.y0 - 3) * s)
        x1, y1 = round((region.x1 + 3) * s), round((region.y1 + 3) * s)
        # Desenhado pelo Pillow, suave como o resto da janela, com os cantos do controle + 3.
        ring = K.ring_image(x1 - x0, y1 - y0, round((region.radius + 3) * s), K.AMBER, max(2, round(2 * s)))
        self._photos["ring"] = ImageTk.PhotoImage(ring)
        canvas.create_image(x0, y0, anchor="nw", image=self._photos["ring"], tags="kbring")

    def _activate(self, _event=None) -> str:
        region = self._region_of(self._kb)
        if region:
            if self._kb[0] == "rail":
                self._rail_action(region)
            elif not region.drag:   # o controle deslizante usa as setas
                region.action()
        return "break"

    def _arrow(self, step: int) -> str | None:
        region = self._region_of(self._kb)
        if region and region.step:
            region.step(step)
            return "break"
        return None