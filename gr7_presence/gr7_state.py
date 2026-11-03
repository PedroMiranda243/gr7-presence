"""Leitura de presets do Guitar Rig 7.

Dois formatos da Native Instruments carregam os mesmos XMLs:

* LastEditBuffer.tle (estado salvo quando o GR7 fecha): blocos zlib
      b"atad" u32(versão) tipo[4] (invertido, ex. b"ofni" = info) b"bilz" u32(comprimido) u32(original) <zlib>
* Rack Presets/*.ngrr (presets de fábrica e do usuário): os XMLs aparecem sem compressão.

XMLs que importam:
    <soundinfo>           nome, autor, banco e tags do preset
    <gr-instrument-chunk> rack completo (cadeia de componentes)
    <user_state>          caminho do último preset carregado (só no .tle)
"""
from __future__ import annotations

import logging
import os
import re
import struct
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_BUFFER_PATH = Path(os.environ.get("LOCALAPPDATA", "")) / "Native Instruments" / "Guitar Rig 7" / "LastEditBuffer.tle"

# Amplificadores do GR7 (tirados dos presets "Basic <amp>" de fábrica) + variações de nome.
KNOWN_AMPS = {
    "AC Box", "Bass Invader", "Bass Pro", "Bass VT", "Chicago", "Citrus", "Cool Plex", "Fire Seeker",
    "Firebreather", "Fire Breather", "Gratifier", "High White", "Hot Plex", "Hot Solo +", "Hot Solo+",
    "Jazz Amp", "Jump", "Lead 800", "Plex", "Rammfire", "Super Fast 100", "Twang Reverb", "Tweed Delight",
    "Tweed Duo", "Tweedman", "Ultrasonic", "Van 51",
}

# Componentes que não são "efeitos" na cadeia (contêineres e utilitários).
_CHAIN_IGNORE = {"Split", "Split B", "Split Mix", "Container", "CrossOver", "CrossOver B", "CrossOver Mix", "Crossover Mix"}


@dataclass
class PresetInfo:
    name: str | None = None
    author: str | None = None
    bank: str | None = None
    edition: str | None = None          # ex.: "Guitar Rig 7 Pro"
    is_factory: bool | None = None
    preset_uri: str | None = None
    amp: str | None = None
    genres: list[str] = field(default_factory=list)
    characters: list[str] = field(default_factory=list)
    fx_types: list[str] = field(default_factory=list)
    input_source: str | None = None      # "Guitar", "Bass"...
    chain: list[str] = field(default_factory=list)   # componentes ligados, na ordem do rack
    saved_at: str | None = None          # atributo "time" gravado pelo GR7
    mtime: float | None = None

    @property
    def tags(self) -> list[str]:
        """Gêneros, tipo de efeito e caráter, sem repetir."""
        out: list[str] = []
        for t in self.genres + self.fx_types + self.characters:
            if t not in out:
                out.append(t)
        return out

    @property
    def effects(self) -> list[str]:
        """Cadeia sem o amplificador."""
        return [c for c in self.chain if c != self.amp]


def read_blocks(data: bytes) -> dict[str, bytes]:
    """Descompacta os blocos zlib do .tle. Chave = tipo legível (info, prst, guis...)."""
    blocks: dict[str, bytes] = {}
    pos = 0
    while True:
        i = data.find(b"atad", pos)
        if i < 0 or i + 24 > len(data):
            break
        pos = i + 4
        kind = data[i + 8:i + 12][::-1].decode("ascii", "replace")
        if data[i + 12:i + 16] != b"bilz":
            continue
        comp_len, _orig_len = struct.unpack_from("<II", data, i + 16)
        start = i + 24
        try:
            raw = zlib.decompressobj().decompress(data[start:start + comp_len])
        except zlib.error:
            continue
        blocks.setdefault(kind, raw)
        pos = start + comp_len
    return blocks


_ROOT_TAG = re.compile(rb"<([A-Za-z_][\w.\-]*)")


def _xml_at(data: bytes, start: int) -> ET.Element | None:
    """Lê o documento XML que começa em `start` (vai até o fechamento da tag raiz)."""
    body = data.find(b"?>", start) + 2 if data.startswith(b"<?xml", start) else start
    m = _ROOT_TAG.search(data, body)
    if not m:
        return None
    end_tag = b"</" + m.group(1) + b">"
    end = data.find(end_tag, m.end())
    if end < 0:
        return None
    try:
        return ET.fromstring(data[start:end + len(end_tag)])
    except ET.ParseError:
        return None


def _xml_docs(data: bytes) -> dict[str, ET.Element]:
    """Todos os XMLs do arquivo, pela tag raiz."""
    docs: dict[str, ET.Element] = {}
    sources = list(read_blocks(data).values()) or [data]
    for raw in sources:
        for m in re.finditer(rb"<\?xml", raw):
            root = _xml_at(raw, m.start())
            if root is not None:
                docs.setdefault(root.tag, root)
    return docs


def _param(component: ET.Element, pid: str) -> str | None:
    p = component.find(f"component-audio/parameters/parameter[@id='{pid}']")
    if p is None:
        p = component.find(f".//parameter[@id='{pid}']")
    return p.get("value") if p is not None else None


def _as_float(v: str | None) -> float | None:
    try:
        return float(v) if v is not None else None
    except ValueError:
        return None


def _parse_soundinfo(root: ET.Element, info: PresetInfo) -> None:
    info.name = (root.findtext("properties/name") or "").strip() or None
    info.author = (root.findtext("properties/author") or "").strip() or None
    info.bank = (root.findtext("banks/bank") or "").strip() or None

    paths: list[list[str]] = []
    for attr in root.findall("attributes/attribute"):
        user_set = attr.findtext("user-set")
        if user_set and user_set.startswith("RP://"):
            paths.append(user_set[5:].split("\t"))
    # Só as folhas: "FX Types/Amps & Cabinets/Hi Gain" vale, "FX Types/Amps & Cabinets" não.
    leaves = [p for p in paths if len(p) >= 2 and not any(len(o) > len(p) and o[:len(p)] == p for o in paths)]
    for p in leaves:
        root_cat, leaf = p[0], p[-1]
        if root_cat == "Amplifiers":
            info.amp = info.amp or leaf
        elif root_cat == "Genres":
            info.genres.append(leaf)
        elif root_cat == "Characters":
            info.characters.append(leaf)
        elif root_cat == "FX Types":
            info.fx_types.append(leaf)
        elif root_cat == "Input Sources":
            info.input_source = info.input_source or leaf


def _parse_rack(root: ET.Element, info: PresetInfo) -> None:
    info.saved_at = root.get("time")
    non_fix = root.find("gr-rack/non-fix-components")
    if non_fix is None:
        return
    for comp in non_fix.iter("component"):
        name = comp.get("name")
        if not name or name in _CHAIN_IGNORE:
            continue
        power = _as_float(_param(comp, "Pwr"))
        if power is not None and power < 0.5:
            continue   # pedal desligado
        info.chain.append(name)
    if info.amp is None:
        info.amp = next((c for c in info.chain if c in KNOWN_AMPS), None)


def _parse_user_state(root: ET.Element, info: PresetInfo) -> None:
    node = root.find(".//last_loaded_preset")
    uri = node.get("value") if node is not None else None
    if not uri:
        return
    info.preset_uri = uri
    # GR7://RackPreset/Factory/Guitar Rig 7 Pro/RTM2 Power
    parts = uri.split("://", 1)[-1].split("/")
    if len(parts) >= 2:
        info.is_factory = parts[1].lower() == "factory"
    if len(parts) >= 4 and info.is_factory:
        info.edition = parts[2]
    if info.name is None and parts:
        info.name = parts[-1]


def parse_buffer(data: bytes) -> PresetInfo | None:
    """Lê um LastEditBuffer.tle ou um preset .ngrr."""
    docs = _xml_docs(data)
    if not docs:
        return None
    sound = docs.get("soundinfo")
    if sound is None and "guitarrig7-database-info" in docs:
        sound = docs["guitarrig7-database-info"].find("soundinfo")
    info = PresetInfo()
    for root, handler in ((sound, _parse_soundinfo),
                          (docs.get("gr-instrument-chunk"), _parse_rack),
                          (docs.get("user_state"), _parse_user_state)):
        if root is not None:
            try:
                handler(root, info)
            except Exception:  # um bloco estranho não derruba os outros
                log.exception("Falha ao ler o bloco %s", root.tag)
    return info


class PresetReader:
    """Relê o arquivo só quando o mtime muda."""

    def __init__(self, path: Path = DEFAULT_BUFFER_PATH):
        self.path = Path(path)
        self._mtime: float | None = None
        self._info: PresetInfo | None = None

    def mtime(self) -> float | None:
        try:
            return self.path.stat().st_mtime
        except OSError:
            return None

    def read(self) -> PresetInfo | None:
        mtime = self.mtime()
        if mtime is None:
            return self._info
        if mtime != self._mtime:
            try:
                info = parse_buffer(self.path.read_bytes())
            except OSError as exc:   # o GR7 pode estar gravando o arquivo agora
                log.debug("Não consegui ler %s: %s", self.path, exc)
                return self._info
            if info is not None:
                info.mtime = mtime
                self._info = info
                self._mtime = mtime
                log.info("Preset salvo no LastEditBuffer: %s (amp %s)", info.name, info.amp)
        return self._info
