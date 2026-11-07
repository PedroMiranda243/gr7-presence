"""Peças visuais da janela do GR7 Presence (direção "Palco"), desenhadas com o Pillow.

O Tkinter não faz cantos arredondados suaves, degradês, luz nem a fonte Archivo. Aqui tudo vira imagem
do Pillow, que o programa já usa: nenhuma dependência nova. As medidas são em pixels lógicos, os mesmos
dos exemplos aprovados (janela de 960 × 640); o `Painter` multiplica pela escala de DPI da tela, para
o desenho ficar nítido em 125 %, 150 % ou 200 %.

As cores e tamanhos vêm dos exemplos aprovados em 2026-11-07 (contrato em `.impeccable/surfaces/`).
"""
from __future__ import annotations

import functools
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

log = logging.getLogger(__name__)

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ARCHIVO = ASSETS / "fonts" / "Archivo.ttf"
WIN_FONTS = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
EMOJI_FONT = WIN_FONTS / "seguiemj.ttf"

# ---- cores ---------------------------------------------------------------------------------------
BG = "#0B0C10"            # o palco
RAIL = "#0F1117"
RAIL_LINE = "#1B1E29"
RAIL_ON = "#1B1E2A"
STAGE = "#11131A"         # painel com luz
PANEL = "#13151C"
PANEL_LINE = "#1E2130"
FIELD = "#151821"
SELECTED = "#272B38"
TRACK = "#232734"
BAR = "#2B3040"
GRID = "#1A1D27"
TEXT = "#F3F1EC"
TEXT_SOFT = "#C9C4BB"
MUTED = "#9EA3B0"
FAINT = "#7A8094"         # 4,6:1 sobre os painéis (o mínimo é 4,5:1)
ICON_OFF = "#8C92A4"
DIM = "#5A6177"
GLOW = "#FFF5EA"
AMBER = "#FFB347"
ORANGE = "#FF5A36"
RED = "#E0141C"
GREEN = "#3DDC97"
CAL_RAMP = ("#1A1D27", "#4A2620", "#8F3A22", "#E0602B", "#FFB347")
SCROLL_THUMB = "#2A2F3D"
FIELD_LINE = "#262A37"
FOCUS_RING = "#3E3124"     # âmbar a 18 % sobre o painel
BAD = "#FF8A6A"
BTN = "#26282E"           # branco a 8 % sobre o painel
BTN_LINE = "#2F3137"
SWITCH_OFF = "#2A2F3D"
CARD = "#1E2027"           # o cartão do Discord na prévia
CARD_LINE = "#2B2D34"
CARD_MUTED = "#B5BAC1"
CARD_BUTTON = "#3A3D46"


# ---- texto ---------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Style:
    """Um estilo de texto, como no CSS dos exemplos: tamanho em pixels lógicos e altura da linha."""
    size: float
    weight: int = 400
    color: str = TEXT
    display: bool = False     # Archivo (títulos e números grandes) em vez da Segoe UI
    width: int = 100          # largura da Archivo (125 = Expanded)
    line: float = 1.3


@functools.lru_cache(maxsize=256)
def _font(display: bool, px: float, weight: int, width: int, opsz: float) -> ImageFont.FreeTypeFont:
    try:
        return _load_font(display, px, weight, width, opsz)
    except TypeError:   # Pillow anterior à 10.1 só aceita tamanho inteiro
        return _load_font(display, max(1, round(px)), weight, width, opsz)


def _load_font(display: bool, px: float, weight: int, width: int, opsz: float) -> ImageFont.FreeTypeFont:
    if display:
        try:
            f = ImageFont.truetype(str(ARCHIVO), px)
            f.set_variation_by_axes([weight, width])   # eixos da Archivo: peso, largura
            return f
        except (OSError, ValueError) as exc:
            log.warning("Sem a fonte Archivo (%s); usando a Segoe UI", exc)
    try:
        f = ImageFont.truetype(str(WIN_FONTS / "SegUIVar.ttf"), px)   # Windows 11
        f.set_variation_by_axes([min(700, max(300, weight)), opsz])  # peso, tamanho óptico
        return f
    except (OSError, ValueError):
        pass
    static = "segoeuib.ttf" if weight >= 700 else "seguisb.ttf" if weight >= 600 else "segoeui.ttf"
    try:
        return ImageFont.truetype(str(WIN_FONTS / static), px)     # Windows 10
    except OSError:
        try:
            return ImageFont.load_default(round(px))
        except TypeError:   # Pillow anterior à 10.1
            return ImageFont.load_default()


def font(style: Style, scale: float) -> ImageFont.FreeTypeFont:
    # Tamanho inteiro: em tamanho pequeno a fonte arredonda a largura de cada letra (hinting), e um
    # tamanho "quebrado" não fica entre os dois vizinhos; ele só muda as quebras de linha de lugar.
    return _font(style.display, max(1, round(style.size * scale)), style.weight, style.width,
                 min(36.0, max(5.0, style.size)))


@functools.lru_cache(maxsize=32)
def _emoji_font(px: float) -> ImageFont.FreeTypeFont | None:
    try:
        return ImageFont.truetype(str(EMOJI_FONT), max(1, round(px)))
    except OSError:
        return None


def _is_emoji(ch: str) -> bool:
    o = ord(ch)
    return (o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2300 <= o <= 0x23FF or 0x2B00 <= o <= 0x2BFF
            or o in (0xFE0F, 0x200D))


def _runs(text: str) -> list[tuple[str, bool]]:
    """Separa o texto em trechos de letras e de emoji: o emoji sai colorido, da Segoe UI Emoji."""
    runs: list[tuple[str, bool]] = []
    for ch in text:
        if ch == "\uFE0F":   # seletor de variação: sem o Raqm, o Pillow desenha um espaço vazio no lugar
            continue
        emoji = _is_emoji(ch)
        if runs and runs[-1][1] == emoji:
            runs[-1] = (runs[-1][0] + ch, emoji)
        else:
            runs.append((ch, emoji))
    return runs


# ---- máscaras e degradês --------------------------------------------------------------------------
SS = 4   # superamostragem: desenha 4× maior e reduz, para as bordas ficarem suaves


@functools.lru_cache(maxsize=256)
def _corner(r: int) -> Image.Image:
    big = Image.new("L", (r * SS * 2, r * SS * 2), 0)
    ImageDraw.Draw(big).ellipse((0, 0, r * SS * 2 - 1, r * SS * 2 - 1), fill=255)
    return big.resize((r * 2, r * 2), Image.LANCZOS).crop((0, 0, r, r))


def rounded_mask(w: int, h: int, r: int) -> Image.Image:
    """Máscara de um retângulo de cantos redondos, com os cantos suavizados."""
    m = Image.new("L", (max(1, w), max(1, h)), 255)
    r = int(min(r, w // 2, h // 2))
    if r <= 0:
        return m
    c = _corner(r)
    m.paste(c, (0, 0))
    m.paste(c.transpose(Image.FLIP_LEFT_RIGHT), (w - r, 0))
    m.paste(c.transpose(Image.FLIP_TOP_BOTTOM), (0, h - r))
    m.paste(c.transpose(Image.ROTATE_180), (w - r, h - r))
    return m


def _rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def gradient(w: int, h: int, top: str, bottom: str, horizontal: bool = False) -> Image.Image:
    """Degradê de duas cores; `horizontal` vai da esquerda para a direita."""
    ramp = Image.linear_gradient("L")
    if horizontal:
        ramp = ramp.rotate(90, expand=True)   # o lado de cima (preto, `top`) vai para a esquerda
    ramp = ramp.resize((max(1, w), max(1, h)))
    return Image.composite(Image.new("RGB", ramp.size, bottom), Image.new("RGB", ramp.size, top), ramp)


def radial_light(w: int, h: int, cx: int, cy: int, rx: int, ry: int,
                 stops: list[tuple[float, tuple[int, int, int, float]]]) -> Image.Image:
    """Luz elíptica em RGBA, do tamanho do painel (w × h, pixels de tela), com centro em (cx, cy) e
    raios rx, ry. `stops` são como os do radial-gradient do CSS: (posição de 0 a 1, (r, g, b, alfa))."""
    dist = Image.radial_gradient("L").resize((max(1, 2 * rx), max(1, 2 * ry)))
    # No radial_gradient do Pillow, a borda do círculo inscrito vale ~181 (128 × √2).
    def channel(i: int):
        lut = []
        for v in range(256):
            t = min(1.0, v / 181.0)
            for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
                if t <= t1:
                    k = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                    a, b = c0[i], c1[i]
                    lut.append(round(((a + (b - a) * k) * (255 if i == 3 else 1))))
                    break
            else:
                lut.append(round(stops[-1][1][i] * (255 if i == 3 else 1)))
        return dist.point(lut)
    light = Image.merge("RGBA", [channel(i) for i in range(4)])
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(light, (cx - rx, cy - ry))
    return out


# ---- ícones (traço, no estilo dos exemplos, caixa de 24 × 24) -------------------------------------
ICONS: dict[str, list[tuple]] = {
    "dash": [("rect", 3, 3, 7, 9, 1.5), ("rect", 14, 3, 7, 5, 1.5), ("rect", 14, 12, 7, 9, 1.5), ("rect", 3, 16, 7, 5, 1.5)],
    "chart": [("path", "M4 20V11M10 20V5M16 20v-6M21 20H3")],
    "sliders": [("path", "M4 6h9M17 6h3M4 12h3M11 12h9M4 18h12"), ("circle", 15, 6, 2), ("circle", 9, 12, 2), ("circle", 18, 18, 2)],
    "up": [("circle", 12, 12, 9), ("path", "M12 16V8M8.5 11.5 12 8l3.5 3.5")],
    "down": [("path", "m6 9 6 6 6-6")],
    "flame": [("path", "M12 21c-3.9 0-7-2.7-7-6.6 0-3.1 2-5 3.5-6.6.3 1.9 1.3 3 2.5 3.4-.4-3.2.8-6.1 3.3-8.2.3 3.4 4.7 5.4 4.7 10.6 0 4.3-3.1 7.4-7 7.4Z")],
    "clock": [("circle", 12, 12, 9), ("path", "M12 7v5l3 2")],
    "target": [("circle", 12, 12, 9), ("circle", 12, 12, 5), ("circle", 12, 12, 1.2)],
    "check": [("path", "M5 12.5 9.8 17.3 19 7.5")],
    "pause": [("path", "M8 5v14M16 5v14")],
    "play": [("path", "M8 5v14l11-7Z")],
    # o amplificador da prévia do cartão (o desenho do exemplo, de 40 para 24)
    "amp": [("path", "M9.6 5.4V3.9h4.8v1.5"), ("rect", 3, 5.4, 18, 13.8, 1.8), ("path", "M3 9h18"),
            ("circle", 6, 7.2, 0.25), ("circle", 8.4, 7.2, 0.25), ("circle", 10.8, 7.2, 0.25)],
    "amp_grille": [("path", "M6 12.3h12M6 14.7h12M6 17.1h12")],
}
_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+)")


def _path_points(d: str) -> list[tuple[list[tuple[float, float]], bool]]:
    """Subconjunto do path do SVG (M L H V C Q Z, absolutos e relativos) em linhas poligonais."""
    out: list[tuple[list[tuple[float, float]], bool]] = []
    pts: list[tuple[float, float]] = []
    x = y = 0.0
    for cmd, args in re.findall(r"([MmLlHhVvCcQqZz])([^MmLlHhVvCcQqZz]*)", d):
        nums = [float(n) for n in _NUM.findall(args)]
        rel = cmd.islower()
        c = cmd.upper()
        if c == "Z":
            if pts:
                out.append((pts, True))
                x, y = pts[0]
            pts = []
            continue
        size = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "Q": 4}[c]
        for i in range(0, len(nums), size):
            a = nums[i:i + size]
            if c in "ML":
                nx, ny = (x + a[0], y + a[1]) if rel else (a[0], a[1])
                if c == "M" and i == 0:
                    if pts:
                        out.append((pts, False))
                    pts = [(nx, ny)]
                else:
                    pts.append((nx, ny))
                x, y = nx, ny
            elif c == "H":
                x = x + a[0] if rel else a[0]
                pts.append((x, y))
            elif c == "V":
                y = y + a[0] if rel else a[0]
                pts.append((x, y))
            else:
                ctrl = [(x + a[k], y + a[k + 1]) if rel else (a[k], a[k + 1]) for k in range(0, size, 2)]
                p0 = (x, y)
                for step in range(1, 13):
                    t = step / 12
                    if c == "C":
                        (x1, y1), (x2, y2), (x3, y3) = ctrl
                        px = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t * t * x2 + t ** 3 * x3
                        py = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t * t * y2 + t ** 3 * y3
                    else:
                        (x1, y1), (x2, y2) = ctrl
                        px = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * x1 + t * t * x2
                        py = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * y1 + t * t * y2
                    pts.append((px, py))
                x, y = ctrl[-1]
    if pts:
        out.append((pts, False))
    return out


@functools.lru_cache(maxsize=128)
def icon_image(name: str, px: int, color: str, stroke: float = 1.8) -> Image.Image:
    """Ícone em RGBA, `px` × `px` pixels de tela."""
    k = px * SS / 24
    big = Image.new("L", (px * SS, px * SS), 0)
    d = ImageDraw.Draw(big)
    w = max(1, round(stroke * k))

    def cap(p):
        r = w / 2
        d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=255)

    for item in ICONS[name]:
        if item[0] == "rect":
            _, x, y, rw, rh, rr = item
            d.rounded_rectangle((x * k, y * k, (x + rw) * k, (y + rh) * k), radius=rr * k, outline=255, width=w)
        elif item[0] == "circle":
            _, cx, cy, r = item
            d.ellipse(((cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k), outline=255, width=w)
        else:
            for pts, closed in _path_points(item[1]):
                scaled = [(px_ * k, py_ * k) for px_, py_ in pts]
                if closed:
                    scaled.append(scaled[0])
                if len(scaled) > 1:
                    d.line(scaled, fill=255, width=w, joint="curve")
                for p in (scaled[0], scaled[-1]):
                    cap(p)
    mask = big.resize((px, px), Image.LANCZOS)
    out = Image.new("RGBA", (px, px), color)
    out.putalpha(mask)
    return out


# ---- o pintor -------------------------------------------------------------------------------------
class Painter:
    """Uma imagem RGB em pixels de tela, desenhada com medidas lógicas (multiplicadas por `scale`)."""

    def __init__(self, width: float, height: float, scale: float, bg: str = BG):
        self.s = scale
        self.img = Image.new("RGB", (self.px(width), self.px(height)), bg)
        self.draw = ImageDraw.Draw(self.img)

    def px(self, v: float) -> int:
        return round(v * self.s)

    # ---- formas ----
    def rect(self, x: float, y: float, w: float, h: float, fill: str) -> None:
        self.draw.rectangle((self.px(x), self.px(y), self.px(x + w) - 1, self.px(y + h) - 1), fill=fill)

    def rrect(self, x: float, y: float, w: float, h: float, r: float, fill: str | Image.Image,
              outline: str | None = None, light: Image.Image | None = None) -> None:
        """Retângulo arredondado; `fill` pode ser uma cor ou uma imagem (degradê) do mesmo tamanho."""
        X, Y, W, H, R = self.px(x), self.px(y), self.px(x + w) - self.px(x), self.px(y + h) - self.px(y), self.px(r)
        if W <= 0 or H <= 0:
            return
        tile = fill.resize((W, H)) if isinstance(fill, Image.Image) else Image.new("RGB", (W, H), fill)
        if light is not None:
            tile = Image.alpha_composite(tile.convert("RGBA"), light.crop((0, 0, W, H))).convert("RGB")
        mask = rounded_mask(W, H, R)
        self.img.paste(tile, (X, Y), mask)
        if outline:
            b = max(1, self.px(1))
            inner = Image.new("L", (W, H), 0)
            inner.paste(rounded_mask(W - 2 * b, H - 2 * b, max(0, R - b)), (b, b))
            self.img.paste(Image.new("RGB", (W, H), outline), (X, Y), ImageChops.subtract(mask, inner))

    def top_rounded_bar(self, x: float, y: float, w: float, h: float, r: float, fill: str | Image.Image) -> None:
        """Barra de gráfico: cantos redondos só em cima."""
        X, Y, W, H = self.px(x), self.px(y), self.px(x + w) - self.px(x), self.px(y + h) - self.px(y)
        if W <= 0 or H <= 0:
            return
        R = min(self.px(r), W // 2, H)
        tile = fill.resize((W, H)) if isinstance(fill, Image.Image) else Image.new("RGB", (W, H), fill)
        mask = rounded_mask(W, H + R, R).crop((0, 0, W, H))
        self.img.paste(tile, (X, Y), mask)

    def circle(self, cx: float, cy: float, r: float, fill: str) -> None:
        R = max(1, self.px(r))
        big = Image.new("L", (R * 2 * SS, R * 2 * SS), 0)
        ImageDraw.Draw(big).ellipse((0, 0, R * 2 * SS - 1, R * 2 * SS - 1), fill=255)
        self.img.paste(fill, (self.px(cx) - R, self.px(cy) - R), big.resize((R * 2, R * 2), Image.LANCZOS))

    def hline(self, x1: float, x2: float, y: float, color: str, width: float = 1, dash: tuple[float, float] | None = None) -> None:
        w = max(1, self.px(width))
        Y = self.px(y) - w // 2
        if not dash:
            self.draw.rectangle((self.px(x1), Y, self.px(x2) - 1, Y + w - 1), fill=color)
            return
        on, off = dash
        x = x1
        while x < x2:
            self.draw.rectangle((self.px(x), Y, self.px(min(x + on, x2)) - 1, Y + w - 1), fill=color)
            x += on + off

    def shadow(self, x: float, y: float, w: float, h: float, r: float, color: tuple[int, int, int, int],
               dy: float, blur: float, spread: float = 0) -> None:
        """Sombra com deslocamento e desfoque, como o box-shadow do CSS."""
        pad = self.px(blur * 2 + abs(spread) + abs(dy))
        W, H = self.px(w + 2 * spread), self.px(h + 2 * spread)
        if W <= 0 or H <= 0:
            return
        mask = Image.new("L", (W + 2 * pad, H + 2 * pad), 0)
        mask.paste(rounded_mask(W, H, self.px(r)), (pad, pad))
        mask = mask.filter(ImageFilter.GaussianBlur(self.px(blur) / 2))
        alpha = mask.point(lambda v: v * color[3] // 255)
        self.img.paste(color[:3], (self.px(x - spread) - pad, self.px(y - spread + dy) - pad), alpha)

    def icon(self, name: str, x: float, y: float, size: float, color: str, stroke: float = 1.8,
             alpha: float = 1.0) -> None:
        img = icon_image(name, self.px(size), color, stroke)
        mask = img.getchannel("A") if alpha >= 1 else img.getchannel("A").point(lambda v: round(v * alpha))
        self.img.paste(img, (self.px(x), self.px(y)), mask)

    def picture(self, path: Path, x: float, y: float, size: float) -> None:
        try:
            img = _picture(str(path), self.px(size))
        except OSError:
            return
        self.img.paste(img, (self.px(x), self.px(y)), img)

    # ---- texto ----
    def measure(self, text: str, style: Style) -> float:
        f = font(style, self.s)
        total = 0.0
        for run, emoji in _runs(text):
            ef = _emoji_font(f.size) if emoji else None
            total += (ef or f).getlength(run)
        return total / self.s

    def text(self, x: float, top: float, text: str, style: Style, anchor: str = "l",
             max_w: float | None = None, color: str | None = None) -> float:
        """Uma linha de texto. `top` é o topo da caixa da linha (altura = tamanho × `line`), como no
        CSS; `anchor` alinha `x` à esquerda (l), no meio (m) ou à direita (r). Devolve a largura."""
        if max_w is not None:
            text = self.fit(text, style, max_w)
        f = font(style, self.s)
        ascent, descent = f.getmetrics()
        line_h = style.size * style.line * self.s
        baseline = round(self.px(top) + (line_h - (ascent + descent)) / 2 + ascent)
        width = self.measure(text, style)
        cx = x * self.s - (width * self.s if anchor == "r" else width * self.s / 2 if anchor == "m" else 0)
        for run, emoji in _runs(text):
            ef = _emoji_font(f.size) if emoji else None
            if ef:
                self.draw.text((round(cx), baseline), run, font=ef, embedded_color=True, anchor="ls")
            else:
                self.draw.text((round(cx), baseline), run, font=f, fill=color or style.color, anchor="ls")
            cx += (ef or f).getlength(run)
        return width

    def baseline_text(self, x: float, baseline: float, text: str, style: Style, color: str | None = None) -> float:
        """Texto apoiado numa linha de base (números grandes ao lado de texto pequeno)."""
        f = font(style, self.s)
        self.draw.text((round(x * self.s), round(baseline * self.s)), text, font=f, fill=color or style.color, anchor="ls")
        return self.measure(text, style)

    def ascent(self, style: Style) -> float:
        return font(style, self.s).getmetrics()[0] / self.s

    def balanced(self, text: str, style: Style, max_w: float) -> list[str]:
        """Quebra em linhas de tamanho parecido (como o text-wrap: balance do CSS) para títulos."""
        lines = self.wrap(text, style, max_w)
        if len(lines) != 2:
            return lines
        words = text.split()
        best = lines
        best_w = max(self.measure(line, style) for line in lines)
        for i in range(1, len(words)):
            a, b = " ".join(words[:i]), " ".join(words[i:])
            wa, wb = self.measure(a, style), self.measure(b, style)
            if max(wa, wb) <= max_w and max(wa, wb) < best_w:
                best, best_w = [a, b], max(wa, wb)
        return best

    def dashed_rrect(self, x: float, y: float, w: float, h: float, r: float, color: str, width: float = 1.5,
                     dash: float = 6, gap: float = 4) -> None:
        """Contorno tracejado de cantos redondos (o cartão vazio do Painel)."""
        X, Y, W, H, R = self.px(x), self.px(y), self.px(x + w) - self.px(x), self.px(y + h) - self.px(y), self.px(r)
        b = max(1, self.px(width))
        outer = rounded_mask(W, H, R)
        inner = Image.new("L", (W, H), 0)
        inner.paste(rounded_mask(W - 2 * b, H - 2 * b, max(0, R - b)), (b, b))
        ring = ImageChops.subtract(outer, inner)
        dashes = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(dashes)
        on, period = self.px(dash), self.px(dash + gap)
        for k in range(R, W - R, period):
            d.rectangle((k, 0, min(k + on, W - R) - 1, H), fill=255)
        for k in range(R, H - R, period):
            d.rectangle((0, k, W, min(k + on, H - R) - 1), fill=255)
        for cx, cy in ((0, 0), (W - R, 0), (0, H - R), (W - R, H - R)):
            d.rectangle((cx, cy, cx + R - 1, cy + R - 1), fill=255)
        self.img.paste(color, (X, Y), ImageChops.multiply(ring, dashes))

    def label(self, x: float, cy: float, text: str, style: Style, anchor: str = "l", color: str | None = None) -> float:
        """Uma linha curta centrada na altura `cy` (rótulos de gráfico)."""
        f = font(style, self.s)
        self.draw.text((round(x * self.s), round(cy * self.s)), text, font=f, fill=color or style.color, anchor=anchor + "m")
        return f.getlength(text) / self.s

    def fit(self, text: str, style: Style, max_w: float) -> str:
        """Corta com reticências o que não cabe em `max_w`."""
        if self.measure(text, style) <= max_w:
            return text
        while text and self.measure(text + "…", style) > max_w:
            text = text[:-1]
        return text.rstrip() + "…"

    def wrap(self, text: str, style: Style, max_w: float) -> list[str]:
        """Quebra em linhas que cabem em `max_w`; um \n no texto força a quebra."""
        lines: list[str] = []
        for part in text.split("\n"):
            line = ""
            for word in part.split():
                trial = f"{line} {word}".strip()
                if line and self.measure(trial, style) > max_w:
                    lines.append(line)
                    line = word
                else:
                    line = trial
            if line:
                lines.append(line)
        return lines

    def paragraph(self, x: float, top: float, text: str, style: Style, max_w: float) -> float:
        """Texto com quebra de linha; devolve a altura usada."""
        lines = self.wrap(text, style, max_w)
        for i, line in enumerate(lines):
            self.text(x, top + i * style.size * style.line, line, style)
        return len(lines) * style.size * style.line


@functools.lru_cache(maxsize=16)
def _picture(path: str, px: int) -> Image.Image:
    return Image.open(path).convert("RGBA").resize((px, px), Image.LANCZOS)


def paragraph_height(painter: Painter, text: str, style: Style, max_w: float) -> float:
    return len(painter.wrap(text, style, max_w)) * style.size * style.line


@dataclass
class Field:
    """Um campo de texto de verdade (tk.Entry), posto pela janela por cima do desenho do campo."""
    key: str
    x: float
    y: float
    w: float
    h: float
    value: str
    placeholder: str = ""
    max_len: int = 512
    on_change: object = None   # função(texto)


@dataclass
class Rendered:
    """Uma página ou barra desenhada: a imagem, a altura em pixels lógicos, as áreas clicáveis e os
    campos de texto."""
    image: Image.Image
    height: float
    regions: list
    fields: list = field(default_factory=list)


@dataclass
class Region:
    """Área clicável de uma imagem, em pixels lógicos."""
    x0: float
    y0: float
    x1: float
    y1: float
    action: object          # função sem argumentos
    key: str = ""
    drag: object = None     # função(x, y) chamada ao clicar e arrastar (o controle deslizante)
    radius: float = 10      # raio dos cantos do controle, para o contorno do teclado acompanhar
    step: object = None     # função(+1 ou -1) para as setas do teclado (o controle deslizante)

    def hit(self, x: float, y: float) -> bool:
        return self.x0 <= x < self.x1 and self.y0 <= y < self.y1


def segmented(p: Painter, right: float, top: float, labels: list[str], selected: int,
              keys: list[str] | None = None, actions: list | None = None) -> tuple[float, float, list[Region]]:
    """Controle de abas pequenas (como "14 dias | 16 semanas | Tudo"), alinhado à direita em `right`.
    Devolve largura, altura e as áreas clicáveis."""
    style = Style(12.5, 600, MUTED, line=1.25)
    widths = [p.measure(t, style) + 24 for t in labels]
    w = sum(widths) + 2 * (len(labels) - 1) + 8
    h = 3 + 6 + style.size * style.line + 6 + 3 + 2
    x0 = right - w
    p.rrect(x0, top, w, h, 11, FIELD, outline=PANEL_LINE)
    regions = []
    x = x0 + 4
    for i, (label, iw) in enumerate(zip(labels, widths)):
        if i == selected:
            p.rrect(x, top + 4, iw, h - 8, 8, SELECTED)
        p.text(x + iw / 2, top + 4 + 6, label, style, anchor="m", color=TEXT if i == selected else MUTED)
        if actions:
            regions.append(Region(x, top + 4, x + iw, top + h - 4, actions[i], (keys or labels)[i], radius=8))
        x += iw + 2
    return w, h, regions


# ---- controles dos Ajustes ------------------------------------------------------------------------
CONTROL = Style(13.5, 400, TEXT, line=1.3)
BUTTON = Style(13, 600, TEXT, line=1.3)


def switch(p: Painter, x: float, y: float, on: bool) -> None:
    """Chave liga/desliga de 38 × 22, acesa no degradê do palco."""
    if on:
        p.rrect(x, y, 38, 22, 11, gradient(p.px(38), p.px(22), AMBER, ORANGE, horizontal=True))
        p.circle(x + 38 - 3 - 8, y + 11, 8, "#FFFFFF")
    else:
        p.rrect(x, y, 38, 22, 11, SWITCH_OFF)
        p.circle(x + 3 + 8, y + 11, 8, "#C9CDD8")


def text_box(p: Painter, x: float, y: float, w: float, h: float = 34, focused: bool = False, bad: bool = False) -> None:
    """O fundo de um campo; o texto vem de um tk.Entry posto por cima, ou de `select_box`."""
    if focused:
        p.rrect(x - 3, y - 3, w + 6, h + 6, 13, FOCUS_RING)
    p.rrect(x, y, w, h, 10, FIELD, outline=AMBER if focused else ORANGE if bad else FIELD_LINE)


def select_box(p: Painter, x: float, y: float, w: float, text: str, focused: bool = False) -> None:
    text_box(p, x, y, w, 34, focused)
    p.text(x + 12, y + (34 - CONTROL.size * CONTROL.line) / 2, text, CONTROL, max_w=w - 44)
    p.icon("down", x + w - 12 - 14, y + 10, 14, MUTED, stroke=2.2)


def select_width(p: Painter, labels: list[str]) -> float:
    return max(p.measure(label, CONTROL) for label in labels) + 12 + 44


def slider(p: Painter, x: float, y: float, w: float, frac: float) -> None:
    """Controle deslizante de 22 de altura; `frac` de 0 a 1."""
    frac = min(1.0, max(0.0, frac))
    p.rrect(x, y + 8, w, 6, 3, TRACK)
    cx = x + 8 + (w - 16) * frac
    if cx - x > 0:
        p.rrect(x, y + 8, cx - x, 6, 3, gradient(p.px(cx - x), p.px(6), AMBER, ORANGE, horizontal=True))
    p.shadow(cx - 8, y + 3, 16, 16, 8, (0, 0, 0, 128), dy=1, blur=4)
    p.circle(cx, y + 11, 8, "#FFFFFF")


def button(p: Painter, x: float, y: float, text: str, anchor: str = "l") -> float:
    """Botão secundário (fundo claro e translúcido); devolve a largura."""
    w = p.measure(text, BUTTON) + 28
    if anchor == "r":
        x -= w
    p.rrect(x, y, w, 34, 10, BTN, outline=BTN_LINE)
    p.text(x + 14, y + (34 - BUTTON.size * BUTTON.line) / 2, text, BUTTON)
    return w


# ---- prévia do Discord -----------------------------------------------------------------------------
CARD_K = Style(11.5, 700, CARD_MUTED, line=1.38)
CARD_TEXT = Style(13, 400, "#F2F3F5", line=1.38)
CARD_APP = Style(13, 700, "#F2F3F5", line=1.38)
CARD_EL = Style(13, 400, CARD_MUTED, line=1.38)
CARD_BTN = Style(12.5, 600, "#F2F3F5", line=1.3)


def discord_card_height(buttons: int) -> float:
    rows = 4 * 13 * 1.38
    return 12 + 11.5 * 1.38 + 8 + max(64, rows) + (10 + buttons * 30 + (buttons - 1) * 6 if buttons else 0) + 13


def discord_card(p: Painter, x: float, y: float, w: float, verb: str, lines: list[str], buttons: list[str]) -> float:
    """O cartão como o Discord mostra no perfil: título, imagem do amplificador e as 4 linhas."""
    h = discord_card_height(len(buttons))
    p.shadow(x, y, w, h, 8, (0, 0, 0, 191), dy=22, blur=44, spread=-14)
    p.rrect(x, y, w, h, 8, CARD, outline=CARD_LINE)
    p.text(x + 12, y + 12, verb, CARD_K)
    top = y + 12 + 11.5 * 1.38 + 8
    rows_h = 4 * 13 * 1.38
    art_y = top + (max(64, rows_h) - 64) / 2
    p.rrect(x + 12, art_y, 64, 64, 8, gradient(p.px(64), p.px(64), "#FF7A3D", "#B50F17"))
    p.icon("amp", x + 12 + 12, art_y + 12, 40, "#FFFFFF", stroke=1.2)
    p.icon("amp_grille", x + 12 + 12, art_y + 12, 40, "#FFFFFF", stroke=0.9, alpha=0.5)
    tx, tw = x + 12 + 64 + 12, w - 12 - 64 - 12 - 12
    ty = top + (max(64, rows_h) - rows_h) / 2
    for i, (line, style) in enumerate(zip(lines, (CARD_APP, CARD_TEXT, CARD_TEXT, CARD_EL))):
        if line:
            p.text(tx, ty + i * 13 * 1.38, line, style, max_w=tw)
    by = top + max(64, rows_h) + 10
    for label in buttons:
        p.rrect(x + 12, by, w - 24, 30, 4, CARD_BUTTON)
        p.text(x + w / 2, by + (30 - 12.5 * 1.3) / 2, label, CARD_BTN, anchor="m", max_w=w - 40)
        by += 36
    return h


MEMBER_NAME = Style(13.5, 600, TEXT, line=1.3)
MEMBER_LINE = Style(12, 400, MUTED, line=1.3)


def member_row(p: Painter, x: float, y: float, w: float, name: str, line: str) -> float:
    """Como a pessoa aparece na lista de membros do servidor."""
    p.rrect(x, y, w, 52, 10, PANEL, outline=PANEL_LINE)
    p.circle(x + 12 + 16, y + 26, 16, "#3A3F52")
    p.text(x + 12 + 16, y + 26 - 6.5, name[:1].upper(), Style(13, 700, TEXT, line=1.0), anchor="m")
    p.circle(x + 12 + 32 - 4, y + 26 + 16 - 4, 7.5, PANEL)
    p.circle(x + 12 + 32 - 4, y + 26 + 16 - 4, 5, GREEN)
    tx = x + 12 + 32 + 10
    p.text(tx, y + 26 - (13.5 * 1.3 + 12 * 1.3) / 2, name, MEMBER_NAME)
    p.text(tx, y + 26 - (13.5 * 1.3 + 12 * 1.3) / 2 + 13.5 * 1.3, line, MEMBER_LINE, max_w=w - (tx - x) - 12)
    return 52