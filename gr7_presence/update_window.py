"""Janela "Atualizar o GR7 Presence": o que muda na versão nova e o botão de atualizar."""
from __future__ import annotations

import re
import tkinter as tk
import webbrowser
from typing import Callable

from .i18n import Translator
from .stats_window import ACCENT, BG, FONT, LOGO, MUTED, PANEL, TEXT
from .updates import Release


def plain_notes(markdown: str) -> str:
    """As notas da release (o trecho do CHANGELOG, em markdown) como texto simples."""
    text = re.sub(r"^#+\s*", "", markdown, flags=re.M)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"^\s*[-*] ", "• ", text, flags=re.M)
    return text.replace("️", "").strip()   # o seletor de emoji vira um espaço em branco no Tk


class UpdateWindow:
    def __init__(self, master: tk.Misc, release: Release, current: str, t: Translator,
                 on_confirm: Callable[[], None]):
        self.release = release
        self.t = t
        self.on_confirm = on_confirm
        self.alive = True
        self.win = tk.Toplevel(master)
        self.win.title(t("update_window_title"))
        self.win.configure(bg=BG)
        # O programa é DPI aware: as fontes crescem com a escala do Windows, os pixels não.
        scale = max(1.0, self.win.winfo_fpixels("1i") / 96)
        self.win.geometry(f"{int(560 * scale)}x{int(540 * scale)}")
        self.win.minsize(int(440 * scale), int(400 * scale))
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        try:
            self.win.iconbitmap(str(LOGO.parent.parent / "tray.ico"))
        except tk.TclError:
            pass

        body = tk.Frame(self.win, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=16)
        tk.Label(body, text=t("update_window_heading", version=release.version), font=(FONT, 16, "bold"),
                 fg=TEXT, bg=BG).pack(anchor="w")
        tk.Label(body, text=t("update_window_current", current=current), font=(FONT, 10),
                 fg=MUTED, bg=BG).pack(anchor="w", pady=(0, 10))

        # De baixo para cima: botões, status e aviso ficam sempre à vista; as notas usam o que sobrar.
        wrap = int(500 * scale)
        buttons = tk.Frame(body, bg=BG)
        buttons.pack(side="bottom", fill="x", pady=(10, 0))
        self.status = tk.Label(body, text="", font=(FONT, 9, "bold"), fg=ACCENT, bg=BG, wraplength=wrap, justify="left")
        self.status.pack(side="bottom", anchor="w")
        tk.Label(body, text=t("update_window_info"), font=(FONT, 9), fg=MUTED, bg=BG, wraplength=wrap,
                 justify="left").pack(side="bottom", anchor="w", pady=(10, 4))

        notes = tk.Frame(body, bg=PANEL)
        notes.pack(fill="both", expand=True)
        scroll = tk.Scrollbar(notes)
        scroll.pack(side="right", fill="y")
        text = tk.Text(notes, wrap="word", bg=PANEL, fg=TEXT, relief="flat", font=(FONT, 10), padx=12, pady=10,
                       height=6, yscrollcommand=scroll.set, highlightthickness=0, borderwidth=0)
        text.insert("1.0", plain_notes(release.notes) or t("update_window_no_notes"))
        text.configure(state="disabled")
        text.pack(side="left", fill="both", expand=True)
        scroll.configure(command=text.yview)

        self.ok = tk.Button(buttons, text=t("update_now"), command=self._confirm, bg=ACCENT, fg="white",
                            activebackground=ACCENT, activeforeground="white", relief="flat",
                            font=(FONT, 10, "bold"), padx=16, pady=6, cursor="hand2")
        self.ok.pack(side="right")
        self.later = tk.Button(buttons, text=t("update_later"), command=self.close, bg=PANEL, fg=TEXT,
                               activebackground=PANEL, activeforeground=TEXT, relief="flat",
                               font=(FONT, 10), padx=14, pady=6, cursor="hand2")
        self.later.pack(side="right", padx=(0, 8))
        link = tk.Label(buttons, text=t("update_page"), font=(FONT, 9, "underline"), fg=MUTED, bg=BG, cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda _e: webbrowser.open(release.url))
        self.focus()

    def _confirm(self) -> None:
        self.ok.configure(state="disabled")
        self.later.configure(state="disabled")
        self.status.configure(text=self.t("update_downloading", version=self.release.version))
        self.on_confirm()

    def show_error(self, message: str) -> None:
        if not self.alive:
            return
        self.ok.configure(state="normal")
        self.later.configure(state="normal")
        self.status.configure(text=self.t("update_failed", error=message))

    def focus(self) -> None:
        self.win.deiconify()
        self.win.lift()
        self.win.attributes("-topmost", True)   # aberta pela bandeja, tende a nascer atrás das outras
        self.win.after(500, lambda: self.alive and self.win.attributes("-topmost", False))
        self.win.focus_force()

    def close(self) -> None:
        self.alive = False
        self.win.destroy()
