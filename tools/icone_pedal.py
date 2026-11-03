"""O ícone do GR7 Presence: um pedal de expressão vermelho, visto de cima, com volume.

    .venv\\Scripts\\python tools\\make_assets.py --icone

Arte original do projeto, desenhada aqui e versionada em assets/gr7_presence.ico e .png. Ela é
bem diferente do ícone do Guitar Rig 7 (quadrado preto com "GR"), para os dois não se confundirem
na barra de tarefas. Coordenadas numa grade de 0 a 100, a mesma do esboço aprovado. Cada tamanho é
desenhado de 4 a 8 vezes maior e reduzido; até 32 px sai uma versão simplificada, sem nervuras nem
anel de LEDs, que viraria borrão.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
SIMPLE_UP_TO = 32

RED = [(0.0, (255, 68, 54)), (0.55, (224, 20, 28)), (1.0, (168, 12, 20))]
RED_DEPTH = (124, 9, 16)
TREADLE = [(0.0, (59, 59, 67)), (1.0, (21, 21, 25))]
TREADLE_DEPTH = (11, 11, 14)
CHROME = [(0.0, (242, 244, 246)), (1.0, (142, 149, 156))]
KNOB = [(0.0, (90, 90, 99)), (1.0, (17, 17, 20))]
LED_OFF = (110, 10, 15)
GREEN = (75, 255, 110)
YELLOW = (255, 210, 63)


def _lut(stops):
    """Rampa de cores (posição 0..1, RGB) -> tabelas de 256 valores por canal."""
    tables = ([], [], [])
    for i in range(256):
        t = i / 255
        for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
            if p0 <= t <= p1:
                k = (t - p0) / (p1 - p0) if p1 > p0 else 0
                for ch in range(3):
                    tables[ch].append(round(c0[ch] + (c1[ch] - c0[ch]) * k))
                break
    return tables


def _paint(gray: Image.Image, stops) -> Image.Image:
    r, g, b = _lut(stops)
    return Image.merge("RGBA", (gray.point(r), gray.point(g), gray.point(b), Image.new("L", gray.size, 255)))


class Canvas:
    def __init__(self, size: int):
        self.size = size
        self.k = size / 100
        self.img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    def box(self, x, y, w, h):
        k = self.k
        return (x * k, y * k, (x + w) * k, (y + h) * k)

    def mask(self, draw_fn) -> Image.Image:
        m = Image.new("L", self.img.size, 0)
        draw_fn(ImageDraw.Draw(m))
        return m

    def fill(self, mask: Image.Image, color, opacity: float = 1.0, blur: float = 0) -> None:
        if blur:
            mask = mask.filter(ImageFilter.GaussianBlur(blur * self.k))
        if opacity < 1:
            mask = mask.point(lambda v: round(v * opacity))
        layer = color.copy() if isinstance(color, Image.Image) else Image.new("RGBA", self.img.size, color)
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
        self.img.alpha_composite(layer)

    def vertical(self, stops) -> Image.Image:
        return _paint(Image.linear_gradient("L").resize(self.img.size), stops)

    def diagonal(self, stops) -> Image.Image:
        v = Image.linear_gradient("L").resize(self.img.size)
        return _paint(ImageChops.add(v, v.transpose(Image.Transpose.ROTATE_90), scale=2), stops)

    def radial(self, cx, cy, r, stops) -> Image.Image:
        """Degradê redondo com o ponto claro em (cx, cy), raio r (na grade de 0 a 100)."""
        k = self.k
        side = max(2, round(2 * r * k))
        disc = Image.radial_gradient("L").resize((side, side))
        gray = Image.new("L", self.img.size, 255)
        gray.paste(disc, (round((cx - r) * k), round((cy - r) * k)))
        return _paint(gray, stops)

    def rrect(self, x, y, w, h, r, color, opacity=1.0, blur=0):
        self.fill(self.mask(lambda d: d.rounded_rectangle(self.box(x, y, w, h), radius=r * self.k, fill=255)),
                  color, opacity, blur)

    def circle(self, cx, cy, r, color, opacity=1.0):
        self.fill(self.mask(lambda d: d.ellipse(self.box(cx - r, cy - r, 2 * r, 2 * r), fill=255)), color, opacity)

    def ellipse(self, cx, cy, rx, ry, color):
        self.fill(self.mask(lambda d: d.ellipse(self.box(cx - rx, cy - ry, 2 * rx, 2 * ry), fill=255)), color)

    def line(self, x0, y0, x1, y1, width, color, opacity=1.0):
        k = self.k
        self.fill(self.mask(lambda d: d.line((x0 * k, y0 * k, x1 * k, y1 * k), fill=255, width=max(1, round(width * k)))),
                  color, opacity)

    def outline(self, x, y, w, h, r, width, color, opacity):
        k = self.k
        self.fill(self.mask(lambda d: d.rounded_rectangle(self.box(x, y, w, h), radius=r * k, outline=255,
                                                          width=max(1, round(width * k)))), color, opacity)


def draw(size: int, simple: bool | None = None) -> Image.Image:
    if simple is None:
        simple = size <= SIMPLE_UP_TO
    scale = 8 if size <= 32 else 4
    c = Canvas(min(size * scale, 1024))

    # Corpo: sombra, a lateral mais escura e o tampo vermelho.
    c.rrect(13, 10, 76, 88, 8, (48, 0, 4, 255), opacity=0.35, blur=2.5)
    c.rrect(10, 8, 76, 88, 8, RED_DEPTH + (255,))
    c.rrect(10, 3, 76, 86, 8, c.diagonal(RED))
    if not simple:
        c.outline(12, 5, 72, 82, 6.5, 1.4, (255, 255, 255, 255), 0.28)

    # Coluna da esquerda: anel de LEDs, knob grande, knob pequeno, LED e footswitch.
    if not simple:
        ring = [(25, 12), (33.5, 15.5), (37, 24), (33.5, 32.5), (16.5, 32.5), (13, 24), (16.5, 15.5)]
        for (x, y), color in zip(ring, [GREEN, YELLOW] + [LED_OFF] * 5):
            c.circle(x, y, 1.7, color + (255,))
    c.circle(25, 24, 9 if simple else 8, c.radial(22, 20.5, 11, KNOB))
    c.line(25, 24, 25, 17, 2.4 if simple else 2, (255, 255, 255, 255))
    if not simple:
        c.circle(25, 46, 4.6, c.radial(23.5, 44.5, 6.5, KNOB))
        c.circle(25, 58, 2.2, GREEN + (255,))
    c.rrect(17, 76, 16, 7, 0, (126, 133, 140, 255))
    c.ellipse(25, 83, 8, 3.4, (110, 116, 122, 255))
    c.ellipse(25, 76, 8, 3.4, c.radial(22, 74.5, 9, CHROME))

    # Pisante: a lateral escura embaixo, o tampo emborrachado, o batente cromado e as nervuras.
    c.rrect(40, 12, 42, 80, 5, TREADLE_DEPTH + (255,))
    c.rrect(40, 6, 42, 80, 5, c.vertical(TREADLE))
    c.rrect(42, 8, 38, 5, 2, c.vertical(CHROME))
    if not simple:
        for y in range(27, 78, 5):
            c.line(44, y, 79, y, 1.7, (69, 69, 78, 255))

    return c.img.resize((size, size), Image.LANCZOS)


def save(ico_path: Path, png_path: Path) -> None:
    images = [draw(s) for s in ICO_SIZES]
    biggest = images[-1]
    biggest.save(png_path)
    biggest.save(ico_path, format="ICO", sizes=[(s, s) for s in ICO_SIZES], append_images=images[:-1])


def preview(path: Path) -> None:
    """Folha de conferência: todos os tamanhos sobre barra escura e clara (não vai para o git)."""
    sizes = [256, 64, 48, 32, 24, 20, 16]
    width = sum(sizes) + 16 * (len(sizes) + 1)
    sheet = Image.new("RGBA", (width, 2 * 280), (32, 32, 32, 255))
    ImageDraw.Draw(sheet).rectangle((0, 280, width, 560), fill=(238, 238, 238, 255))
    for row in (0, 280):
        x = 16
        for s in sizes:
            icon = draw(s)
            sheet.alpha_composite(icon, (x, row + (280 - s) // 2))
            x += s + 16
    sheet.save(path)
