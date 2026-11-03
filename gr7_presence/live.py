"""Estado ao vivo do Guitar Rig 7, lido da própria janela e dos arquivos que ele mantém abertos.

O GR7 só grava o LastEditBuffer.tle quando fecha, o título da janela é sempre "Guitar Rig 7" e a
interface (Qt Quick) não expõe o nome do preset para a acessibilidade. Então:

* preset: captura a janela com PrintWindow (funciona mesmo atrás de outras janelas) e lê o topo do
  rack com o OCR nativo do Windows; o texto é conferido com a biblioteca de presets.
* backing track: arquivos de áudio que o processo do GR7 está segurando abertos (Tape Deck).
"""
from __future__ import annotations

import asyncio
import ctypes
import logging
import os
import re
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

import psutil
from PIL import Image, ImageOps

from .preset_library import PresetLibrary

log = logging.getLogger(__name__)

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
user32.GetDC.restype = wintypes.HDC
user32.GetDC.argtypes = [wintypes.HWND]
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, wintypes.LPVOID,
                            wintypes.LPVOID, wintypes.UINT]

PW_CLIENTONLY, PW_RENDERFULLCONTENT = 0x1, 0x2
_EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

AUDIO_EXTENSIONS = {".wav", ".mp3", ".aif", ".aiff", ".flac", ".ogg", ".m4a", ".wma"}
GR7_TEMP = (Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            / "Native Instruments" / "Guitar Rig 7" / "Temp").as_posix().lower()
_STOPWORDS = {"presets", "components", "signal flow", "search", "curated", "guitar rig", "init"}

# Trechos removidos do nome do arquivo do Tape Deck para virar "Artista Música".
_TRACK_NOISE = [
    r"\bguitar\s*backing\s*track\b", r"\bbacking\s*track\b", r"\bjam\s*track\b", r"\bguitarless\b",
    r"\bno\s*guitars?\b", r"\bwithout\s*guitars?\b", r"\bw/?\s*o?riginal\s*vocals\b", r"\bwith\s*vocals\b",
    r"\bno\s*vocals\b", r"\binstrumental\b", r"\bkaraoke\b", r"\bofficial\s*(audio|video)?\b",
    r"\b(hq|hd|4k|1080p|720p)\b", r"\b\d{2,3}\s*bpm\b",
]


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


def set_dpi_aware() -> None:
    """Coordenadas e capturas em pixels reais (sem a escala do Windows)."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        user32.SetProcessDPIAware()


def main_window(pid: int) -> int | None:
    """Maior janela visível do processo."""
    found: list[tuple[int, int]] = []

    def callback(hwnd, _lparam):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            r = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(r))
            found.append((r.right * r.bottom, hwnd))
        return True

    user32.EnumWindows(_EnumWindowsProc(callback), 0)
    return max(found)[1] if found else None


def capture(hwnd: int) -> Image.Image | None:
    if user32.IsIconic(hwnd):
        return None   # minimizada não renderiza
    r = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    w, h = r.right, r.bottom
    if w < 50 or h < 50:
        return None
    hdc = user32.GetDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    old = gdi32.SelectObject(mdc, bmp)
    try:
        if not user32.PrintWindow(hwnd, mdc, PW_CLIENTONLY | PW_RENDERFULLCONTENT):
            return None
        header = _BITMAPINFOHEADER(ctypes.sizeof(_BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(w * h * 4)
        if not gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(header), 0):
            return None
        return Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
    finally:
        gdi32.SelectObject(mdc, old)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mdc)
        user32.ReleaseDC(hwnd, hdc)


class Ocr:
    """OCR nativo do Windows (Windows.Media.Ocr)."""

    def __init__(self):
        self._engine = None
        self.available = True

    def _get_engine(self):
        if self._engine is None and self.available:
            try:
                from winrt.windows.media.ocr import OcrEngine
                self._engine = OcrEngine.try_create_from_user_profile_languages()
            except Exception as exc:
                log.warning("OCR do Windows indisponível: %s", exc)
                self._engine = None
            if self._engine is None:
                self.available = False
        return self._engine

    def lines(self, image: Image.Image) -> list[tuple[str, int, int]]:
        """[(texto, x, y)] de cada linha reconhecida."""
        engine = self._get_engine()
        if engine is None:
            return []
        from winrt.windows.graphics.imaging import BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap
        from winrt.windows.storage.streams import DataWriter

        rgba = image.convert("RGBA")
        writer = DataWriter()
        writer.write_bytes(rgba.tobytes("raw", "BGRA"))
        bitmap = SoftwareBitmap(BitmapPixelFormat.BGRA8, rgba.width, rgba.height, BitmapAlphaMode.PREMULTIPLIED)
        bitmap.copy_from_buffer(writer.detach_buffer())

        async def recognize():
            return await engine.recognize_async(bitmap)

        result = asyncio.run(recognize())
        out = []
        for line in result.lines:
            rect = line.words[0].bounding_rect if line.words else None
            out.append((line.text, int(rect.x) if rect else 0, int(rect.y) if rect else 0))
        return out


OCR_SCALE = 2


def prepare_for_ocr(band: Image.Image, scale: int = OCR_SCALE) -> Image.Image:
    """Texto escuro em fundo claro, contraste máximo e ampliado.

    O nome do preset tem ~12 px de altura; nesse tamanho o OCR do Windows descarta palavras
    curtas em maiúsculas ("IVP Bass" vira "Bass"). Em 2x ele lê certo.
    """
    gray = ImageOps.autocontrast(ImageOps.invert(band.convert("L")))
    return gray.resize((gray.width * scale, gray.height * scale), Image.LANCZOS)


def rack_is_empty(image: Image.Image, name_x: int, name_y: int) -> bool | None:
    """True se a área do rack, abaixo do nome do preset, está vazia.

    Com o rack limpo ("Clear Rack") o Guitar Rig continua mostrando o nome do último preset, mas
    a área dos componentes fica de uma cor só. Medido: rack vazio = 0% de pixels claros; o rack
    mais simples testado (IVP Bass, 2 componentes) = 12,7%; racks cheios = 35% a 67%.
    """
    box = (max(0, name_x - 6), name_y + 50, min(image.width - 20, name_x + 700), image.height - 30)
    if box[2] - box[0] < 100 or box[3] - box[1] < 100:
        return None
    hist = image.crop(box).convert("L").histogram()
    bright = sum(hist[60:]) / max(1, sum(hist))
    return bright < 0.005


@dataclass
class LiveReading:
    name: str | None          # nome no topo do rack
    rack_empty: bool | None   # None quando não deu para medir


class LivePresetReader:
    ANCHOR_TOLERANCE = (60, 24)   # x, y (pixels da imagem ampliada)

    def __init__(self, library: PresetLibrary, ocr: Ocr | None = None):
        self.library = library
        self.ocr = ocr or Ocr()
        self._last_pick: str | None = None
        self._anchor: tuple[int, int] | None = None   # onde o nome do preset apareceu da última vez

    def read(self, pid: int) -> LiveReading | None:
        """O que aparece agora no Guitar Rig, ou None se não deu para ler (ex.: minimizado)."""
        if not self.ocr.available:
            return None
        hwnd = main_window(pid)
        image = capture(hwnd) if hwnd else None
        if image is None:
            return None
        band = image.crop((0, 0, image.width, min(image.height, max(int(image.height * 0.22), 180))))
        try:
            lines = self.ocr.lines(prepare_for_ocr(band))
        except Exception as exc:
            log.debug("OCR falhou: %s", exc)
            return None
        name = self.pick(lines)
        empty = None
        if name and self._anchor:
            empty = rack_is_empty(image, self._anchor[0] // OCR_SCALE, self._anchor[1] // OCR_SCALE)
        return LiveReading(name, empty)

    def pick(self, lines: list[tuple[str, int, int]]) -> str | None:
        """O nome do preset é a linha mais alta que bate com um preset conhecido.

        Sem nenhum preset conhecido na tela (ex.: preset salvo fora da biblioteca), vale o texto
        que está onde o nome do preset apareceu da última vez.
        """
        candidates = [(text, x, y) for text, x, y in lines if text.strip().lower() not in _STOPWORDS]
        best: tuple[int, float, str, int] | None = None
        for text, x, y in candidates:
            match = self.library.match(text)
            if match is None:
                continue
            name, score = match
            if best is None or (y, -score) < (best[0], -best[1]):
                best = (y, score, name, x)
        if best:
            picked = best[2]
            self._anchor = (best[3], best[0])
        else:
            picked = self._text_at_anchor(candidates)
        if picked != self._last_pick:   # só registra quando muda
            log.debug("OCR: %r -> %s", [t for t, _, _ in lines], picked)
            self._last_pick = picked
        return picked

    def _text_at_anchor(self, candidates: list[tuple[str, int, int]]) -> str | None:
        if not self._anchor:
            return None
        ax, ay = self._anchor
        tx, ty = self.ANCHOR_TOLERANCE
        for text, x, y in candidates:
            name = " ".join(text.split()).strip(" *•·-")
            if abs(x - ax) <= tx and abs(y - ay) <= ty and len(name) >= 2:
                return name
        return None


def clean_track_name(filename: str) -> str | None:
    stem = Path(filename.replace("\\", "/")).stem
    text = re.sub(r"[_]+", " ", stem)
    for pat in _TRACK_NOISE:
        text = re.sub(pat, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[\(\[\{]\s*[\)\]\}]", " ", text)   # parênteses que ficaram vazios
    text = re.sub(r"\s{2,}", " ", text).strip(" -_.,|")
    return text or None


def is_user_track(path: str) -> bool:
    """Arquivo de áudio do usuário (não as gravações/temporários do próprio Tape Deck)."""
    p = Path(path)
    if p.suffix.lower() not in AUDIO_EXTENSIONS:
        return False
    if p.as_posix().lower().startswith(GR7_TEMP):
        return False
    return not p.name.lower().startswith("tapedeck")


def loaded_tracks(pid: int) -> list[str]:
    """Faixas abertas no Tape Deck agora (nomes limpos)."""
    try:
        files = psutil.Process(pid).open_files()
    except (psutil.Error, OSError):
        return []
    names = []
    for f in files:
        if is_user_track(f.path):
            name = clean_track_name(f.path)
            if name and name not in names:
                names.append(name)
    return names
