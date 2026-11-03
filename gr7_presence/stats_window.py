"""Janela de estatísticas (tkinter), com o visual escuro do Discord."""
from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageTk

from .i18n import Translator, format_duration
from .stats import Stats

LOGO = Path(__file__).resolve().parent.parent / "assets" / "discord" / "gr7_logo.png"

BG = "#1E1F22"
PANEL = "#2B2D31"
TEXT = "#F2F3F5"
MUTED = "#B5BAC1"
ACCENT = "#F2572B"
BAR_BG = "#383A40"
FONT = "Segoe UI"


class StatsWindow:
    REFRESH_MS = 10_000

    def __init__(self, master: tk.Misc, stats: Stats, t: Translator):
        self.stats = stats
        self.t = t
        self.win = tk.Toplevel(master)
        self.win.title(t("stats_title"))
        self.win.configure(bg=BG)
        self.win.geometry("560x820")
        self.win.minsize(480, 520)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        try:
            self.win.iconbitmap(str(LOGO.parent.parent / "tray.ico"))
        except tk.TclError:
            pass
        self.alive = True
        self._logo = None
        self.body = tk.Frame(self.win, bg=BG)
        self.body.pack(fill="both", expand=True, padx=18, pady=16)
        self.render()
        self.focus()

    def focus(self) -> None:
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()

    def close(self) -> None:
        self.alive = False
        self.win.destroy()

    # ---- desenho -------------------------------------------------------------------------
    def render(self) -> None:
        if not self.alive:
            return
        for child in self.body.winfo_children():
            child.destroy()
        s = self.stats.summary(top=5, recent=6)
        t = self.t

        header = tk.Frame(self.body, bg=BG)
        header.pack(fill="x")
        try:
            self._logo = ImageTk.PhotoImage(Image.open(LOGO).resize((52, 52), Image.LANCZOS))
            tk.Label(header, image=self._logo, bg=BG).pack(side="left")
        except OSError:
            pass
        titles = tk.Frame(header, bg=BG)
        titles.pack(side="left", padx=12)
        tk.Label(titles, text="Guitar Rig 7", font=(FONT, 16, "bold"), fg=TEXT, bg=BG).pack(anchor="w")
        tk.Label(titles, text=t("stats_title").split("·")[-1].strip(), font=(FONT, 10), fg=MUTED, bg=BG).pack(anchor="w")

        tiles = tk.Frame(self.body, bg=BG)
        tiles.pack(fill="x", pady=(14, 6))
        values = [
            (t("stats_today"), format_duration(s.today)),
            (t("stats_week"), format_duration(s.week)),
            (t("stats_total"), format_duration(s.total)),
            (t("stats_sessions"), str(s.sessions)),
            (t("stats_streak"), t("stats_days", n=s.streak)),
            (t("stats_best_streak"), t("stats_days", n=s.best_streak)),
        ]
        for i, (label, value) in enumerate(values):
            tile = tk.Frame(tiles, bg=PANEL, padx=12, pady=8)
            tile.grid(row=i // 3, column=i % 3, sticky="nsew", padx=4, pady=4)
            tk.Label(tile, text=value, font=(FONT, 15, "bold"), fg=ACCENT if i == 4 and s.streak >= 2 else TEXT,
                     bg=PANEL).pack(anchor="w")
            tk.Label(tile, text=label, font=(FONT, 9), fg=MUTED, bg=PANEL).pack(anchor="w")
        for col in range(3):
            tiles.columnconfigure(col, weight=1, uniform="tiles")

        if s.total <= 0:
            tk.Label(self.body, text=t("stats_empty"), font=(FONT, 10), fg=MUTED, bg=BG,
                     wraplength=480, justify="left").pack(anchor="w", pady=20)
        else:
            self._ranking(t("stats_top_presets"), s.top_presets)
            self._ranking(t("stats_top_amps"), s.top_amps)
            self._recent(s.recent)
        self.win.after(self.REFRESH_MS, self.render)

    def _section(self, title: str) -> tk.Frame:
        tk.Label(self.body, text=title.upper(), font=(FONT, 9, "bold"), fg=MUTED, bg=BG).pack(anchor="w", pady=(12, 4))
        frame = tk.Frame(self.body, bg=PANEL, padx=12, pady=8)
        frame.pack(fill="x")
        return frame

    def _ranking(self, title: str, rows: list[tuple[str, float]]) -> None:
        if not rows:
            return
        frame = self._section(title)
        top = rows[0][1] or 1
        for name, secs in rows:
            line = tk.Frame(frame, bg=PANEL)
            line.pack(fill="x", pady=2)
            tk.Label(line, text=name, font=(FONT, 10), fg=TEXT, bg=PANEL, width=22, anchor="w").pack(side="left")
            bar = tk.Canvas(line, height=10, bg=BAR_BG, highlightthickness=0)
            bar.pack(side="left", fill="x", expand=True, padx=8)
            bar.bind("<Configure>", lambda e, c=bar, k=secs / top: (c.delete("all"),
                     c.create_rectangle(0, 0, max(4, e.width * k), 10, fill=ACCENT, width=0)))
            tk.Label(line, text=format_duration(secs), font=(FONT, 10), fg=MUTED, bg=PANEL, width=7,
                     anchor="e").pack(side="right")

    def _recent(self, sessions: list[dict]) -> None:
        if not sessions:
            return
        frame = self._section(self.t("stats_recent"))
        live = self.stats.current
        for sess in sessions:
            when = datetime.fromtimestamp(sess.get("start", 0)).strftime("%d/%m %H:%M")
            is_live = live is not None and sess.get("start") == live.get("start")
            what = sess.get("last_preset") or sess.get("host") or "Guitar Rig 7"
            line = tk.Frame(frame, bg=PANEL)
            line.pack(fill="x", pady=1)
            tk.Label(line, text=when, font=(FONT, 10), fg=MUTED, bg=PANEL, width=12, anchor="w").pack(side="left")
            tk.Label(line, text=what, font=(FONT, 10), fg=TEXT, bg=PANEL, anchor="w").pack(side="left")
            dur = self.t("stats_live") if is_live else format_duration(sess.get("seconds", 0))
            tk.Label(line, text=dur, font=(FONT, 10, "bold" if is_live else "normal"),
                     fg=ACCENT if is_live else MUTED, bg=PANEL).pack(side="right")
