"""Gera o ícone do programa e as imagens do Rich Presence.

    .venv\\Scripts\\python tools\\make_assets.py                         # todas
    .venv\\Scripts\\python tools\\make_assets.py --icone                 # só o ícone do programa
    .venv\\Scripts\\python tools\\make_assets.py --icone-de arte.png     # troca a arte do ícone
    .venv\\Scripts\\python tools\\make_assets.py --locais                # só as tiradas do Guitar Rig

- gr7_presence.ico / .png: o ícone do programa (barra de tarefas, janelas, bandeja, atalhos), feito
  a partir de gr7_presence_fonte.png por tools/icone.py. Arte do projeto, versionada.
- gr7_logo.png / app_icon.png / tray.ico: ícone oficial tirado do "Guitar Rig 7.exe", só para o app
  do Discord (docs/app-do-discord.md). É arte da Native Instruments: não vai para o repositório nem
  para o zip, e o programa não depende dela.
- amp, pedal, tape, clock, fire, metronome, daw: ícones pequenos do perfil, desenhados aqui (o
  Discord recorta em círculo). Também do projeto e versionados.
"""
from __future__ import annotations

import io
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import icone  # noqa: E402
from exe_icon import extract_ico  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "discord"
EXE = r"C:\Program Files\Native Instruments\Guitar Rig 7\Guitar Rig 7.exe"

SIZE = 1024
S = SIZE * 2          # desenha em 2x e reduz (antialiasing)
C = S // 2
WHITE = (255, 255, 255, 255)


def official_icon() -> Image.Image:
    ico = Image.open(io.BytesIO(extract_ico(EXE)))
    ico.size = max(ico.info["sizes"])
    return ico.convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)


def logo_for_presence(icon: Image.Image) -> Image.Image:
    # O "GR" ocupa só o meio do ícone; um zoom deixa a marca legível no tamanho do Discord.
    margin = int(SIZE * 0.15)
    return icon.crop((margin, margin, SIZE - margin, SIZE - margin)).resize((SIZE, SIZE), Image.LANCZOS)


def canvas(bg: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (S, S), bg)
    return img, ImageDraw.Draw(img)


def finish(img: Image.Image) -> Image.Image:
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def amp() -> Image.Image:
    bg = "#F2572B"
    img, d = canvas(bg)
    d.rounded_rectangle((840, 430, 1208, 640), radius=60, outline=WHITE, width=56)      # alça
    d.rounded_rectangle((404, 560, 1644, 1500), radius=100, fill=WHITE)                  # corpo
    for i in range(5):                                                                   # knobs
        x = 620 + i * 202
        d.ellipse((x - 44, 680, x + 44, 768), fill=bg)
    d.rounded_rectangle((510, 850, 1538, 1400), radius=60, fill=bg)                      # tela
    for y in (980, 1125, 1270):
        d.rounded_rectangle((600, y - 22, 1448, y + 22), radius=22, fill=WHITE)
    return finish(img)


def pedal() -> Image.Image:
    bg = "#7C4DFF"
    img, d = canvas(bg)
    d.rounded_rectangle((624, 360, 1424, 1688), radius=120, fill=WHITE)
    for x in (844, 1204):
        d.ellipse((x - 100, 520, x + 100, 720), fill=bg)
        d.line((x, 620, x, 540), fill=WHITE, width=34)
    d.ellipse((1024 - 42, 860, 1024 + 42, 944), fill=bg)                                # LED
    d.ellipse((1024 - 165, 1180, 1024 + 165, 1510), fill=bg)                            # footswitch
    d.ellipse((1024 - 100, 1245, 1024 + 100, 1445), fill=WHITE)
    return finish(img)


def tape() -> Image.Image:
    bg = "#00A99D"
    img, d = canvas(bg)
    d.rounded_rectangle((324, 584, 1724, 1464), radius=110, fill=WHITE)
    d.rounded_rectangle((494, 734, 1554, 1134), radius=70, fill=bg)
    for x in (784, 1264):
        d.ellipse((x - 130, 804, x + 130, 1064), fill=WHITE)
        d.ellipse((x - 52, 882, x + 52, 986), fill=bg)
    d.polygon([(694, 1464), (824, 1294), (1224, 1294), (1354, 1464)], fill=bg)
    return finish(img)


def clock() -> Image.Image:
    bg = "#2F80ED"
    img, d = canvas(bg)
    d.ellipse((C - 660, C - 660, C + 660, C + 660), fill=WHITE)
    d.ellipse((C - 545, C - 545, C + 545, C + 545), fill=bg)
    d.line((C, C, C, C - 400), fill=WHITE, width=96)
    d.line((C, C, C + 300, C + 170), fill=WHITE, width=96)
    for (x, y) in ((C, C - 400), (C + 300, C + 170)):
        d.ellipse((x - 48, y - 48, x + 48, y + 48), fill=WHITE)
    d.ellipse((C - 90, C - 90, C + 90, C + 90), fill=WHITE)
    return finish(img)


def _teardrop(cx: float, cy: float, w: float, h: float, tilt: float, m: float = 1.6) -> list[tuple[float, float]]:
    pts = []
    for i in range(361):
        t = math.radians(i)
        x = cx + w * math.sin(t) * math.sin(t / 2) ** m + tilt * (1 + math.cos(t)) / 2
        y = cy - h * math.cos(t)
        pts.append((x, y))
    return pts


def fire() -> Image.Image:
    img = Image.new("RGBA", (S, S))
    top, bottom = (255, 179, 0), (255, 61, 0)
    grad = ImageDraw.Draw(img)
    for y in range(S):
        k = y / (S - 1)
        grad.line((0, y, S, y), fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bottom)) + (255,))
    d = ImageDraw.Draw(img)
    d.polygon(_teardrop(C + 10, 1060, 560, 720, tilt=170, m=2.6), fill=WHITE)            # chama principal
    d.polygon(_teardrop(C - 330, 1300, 250, 470, tilt=-120, m=2.2), fill=WHITE)         # língua da esquerda
    d.polygon(_teardrop(C + 360, 1360, 210, 380, tilt=110, m=2.2), fill=WHITE)          # língua da direita
    d.ellipse((C - 530, 1090, C + 530, 1800), fill=WHITE)                                # base
    d.polygon(_teardrop(C + 10, 1390, 230, 330, tilt=60, m=2.0), fill=(255, 112, 0, 255))
    return finish(img)


def metronome() -> Image.Image:
    bg, ink = "#F5B700", (27, 27, 27, 255)
    img, d = canvas(bg)
    d.polygon([(704, 1600), (1344, 1600), (1164, 404), (884, 404)], fill=ink)
    d.polygon([(824, 1480), (1224, 1480), (1104, 560), (944, 560)], fill=bg)
    d.rounded_rectangle((640, 1540, 1408, 1680), radius=40, fill=ink)
    d.line((1024, 1400, 1310, 600), fill=ink, width=70)
    d.rounded_rectangle((1150, 880, 1300, 990), radius=24, fill=ink)
    return finish(img)


def daw() -> Image.Image:
    bg = "#3D5AFE"
    img, d = canvas(bg)
    for x, cap in ((744, 1200), (1024, 760), (1304, 1020)):
        d.rounded_rectangle((x - 26, 480, x + 26, 1568), radius=26, fill=WHITE)
        d.rounded_rectangle((x - 110, cap - 62, x + 110, cap + 62), radius=34, fill=WHITE)
        d.line((x - 70, cap, x + 70, cap), fill=bg, width=22)
    return finish(img)


def main() -> None:
    assets = ROOT / "assets"
    if "--icone-de" in sys.argv:
        art = Path(sys.argv[sys.argv.index("--icone-de") + 1])
        icone.import_art(Image.open(art)).save(assets / "gr7_presence_fonte.png")
        print("Arte nova recortada em", assets / "gr7_presence_fonte.png")
    if "--locais" not in sys.argv:
        icone.save(assets / "gr7_presence_fonte.png", assets / "gr7_presence.ico", assets / "gr7_presence.png")
        print("Ícone do programa gerado em", assets)
        if "--icone" in sys.argv or "--icone-de" in sys.argv:
            return
    OUT.mkdir(parents=True, exist_ok=True)
    if not Path(EXE).exists():
        sys.exit(f"Não achei o Guitar Rig 7 em {EXE}: as imagens do Discord tiradas dele não foram geradas.")
    icon = official_icon()
    icon.save(OUT / "app_icon.png")
    logo_for_presence(icon).save(OUT / "gr7_logo.png")
    if "--locais" in sys.argv:
        print("Ícone do Guitar Rig copiado para", OUT)
        return
    for name, make in (("amp", amp), ("pedal", pedal), ("tape", tape), ("clock", clock),
                       ("fire", fire), ("metronome", metronome), ("daw", daw)):
        make().save(OUT / f"{name}.png")
    preview(sorted(OUT.glob("*.png")))
    print("Imagens geradas em", OUT)


def preview(paths: list[Path]) -> None:
    """Folha de conferência: cada ícone como o Discord mostra (pequenos em círculo)."""
    tile = 160
    sheet = Image.new("RGBA", (tile * len(paths), tile), "#2B2D31")
    mask = Image.new("L", (tile - 20, tile - 20), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, tile - 21, tile - 21), fill=255)
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGBA").resize((tile - 20, tile - 20), Image.LANCZOS)
        if p.stem not in ("app_icon", "gr7_logo"):
            im.putalpha(mask)
        sheet.alpha_composite(im, (i * tile + 10, 10))
    sheet.save(ROOT / "assets" / "preview.png")


if __name__ == "__main__":
    main()
