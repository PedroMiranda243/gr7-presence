"""O ícone do GR7 Presence: o selo vermelho com o pedal de expressão branco.

    .venv\\Scripts\\python tools\\make_assets.py --icone                   # refaz o .ico e o .png
    .venv\\Scripts\\python tools\\make_assets.py --icone-de imagem.png     # troca a arte

A arte foi feita pelo dono do projeto num gerador de imagens e fica em assets/gr7_presence_fonte.png
(1024 px, fundo transparente). Uma arte nova pode chegar com fundo branco: import_art() recorta o
círculo. Até 32 px o pedal é ampliado dentro do círculo e as bordas são reforçadas, porque na escala
da barra de tarefas ele viraria um risco fino.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
SMALL_UP_TO = 32
SMALL_ZOOM = 1.2
SOURCE_SIZE = 1024


def _circle_mask(size: int, cx: float, cy: float, r: float) -> Image.Image:
    k = 4   # desenhado em 4x e reduzido: borda suave
    mask = Image.new("L", (size * k, size * k), 0)
    ImageDraw.Draw(mask).ellipse(((cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k), fill=255)
    return mask.resize((size, size), Image.LANCZOS)


def import_art(image: Image.Image, white: int = 235, inset: float = 2.0, margin: float = 0.02) -> Image.Image:
    """Arte num fundo claro -> o círculo sobre fundo transparente, ocupando o quadrado todo."""
    rgb = image.convert("RGB")
    left, top, right, bottom = rgb.convert("L").point(lambda v: 255 if v < white else 0).getbbox()
    cx, cy = (left + right) / 2, (top + bottom) / 2
    r = min(right - left, bottom - top) / 2 - inset   # um pouco para dentro: nada de franja branca
    side = 2 * r * (1 + margin)
    box = (round(cx - side / 2), round(cy - side / 2), round(cx + side / 2), round(cy + side / 2))
    art = rgb.crop(box).resize((SOURCE_SIZE, SOURCE_SIZE), Image.LANCZOS).convert("RGBA")
    c = SOURCE_SIZE / 2
    art.putalpha(_circle_mask(SOURCE_SIZE, c, c, c / (1 + margin)))
    return art


def render(source: Image.Image, size: int) -> Image.Image:
    if size > SMALL_UP_TO:
        return source.resize((size, size), Image.LANCZOS)
    # Pedal maior dentro do mesmo círculo: amplia o centro e recorta o círculo de novo.
    s = source.width
    inner = round(s / SMALL_ZOOM)
    off = (s - inner) // 2
    zoomed = source.crop((off, off, off + inner, off + inner)).resize((s, s), Image.LANCZOS)
    zoomed.putalpha(source.getchannel("A"))
    small = zoomed.resize((size, size), Image.LANCZOS)
    return small.filter(ImageFilter.UnsharpMask(radius=0.6, percent=60, threshold=2))


def save(source_path: Path, ico_path: Path, png_path: Path) -> None:
    source = Image.open(source_path).convert("RGBA")
    images = [render(source, s) for s in ICO_SIZES]
    images[-1].save(png_path)
    images[-1].save(ico_path, format="ICO", sizes=[(s, s) for s in ICO_SIZES], append_images=images[:-1])
