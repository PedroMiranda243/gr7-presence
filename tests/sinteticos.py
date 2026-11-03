"""Arquivos do Guitar Rig 7 de mentira, para os testes.

O repositório é público: nada de LastEditBuffer.tle de alguém nem preset de fábrica da Native
Instruments. Os bytes saem daqui, com a mesma forma que o programa lê nos arquivos reais (ver
gr7_presence/gr7_state.py) e nomes inventados. Os testes contra os arquivos de verdade ficam em
test_instalacao_real.py e só rodam onde o Guitar Rig 7 está instalado.
"""
from __future__ import annotations

import struct
import zlib
from xml.sax.saxutils import escape

XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n'

# Preset salvo no LastEditBuffer.tle: amp Van 51, metal, com um pedal desligado no meio.
RIFF = dict(
    name="Riff Pesado",
    author="Autora Fictícia",
    bank="Banco de Teste",
    tags=[("Amplifiers", "Van 51"), ("Genres", "Metal"), ("FX Types", "Amps & Cabinets", "Hi Gain"),
          ("Characters", "Distorted"), ("Input Sources", "Guitar")],
    components=["Skreamer", "Van 51", "Control Room Pro", ("Delay Man", False), "PsycheDelay", "Vintage Verb"],
    uri="GR7://RackPreset/Factory/Guitar Rig 7 Pro/Riff Pesado",
)

# Preset .ngrr: cadeia longa (6 efeitos além do amp), para testar o encurtamento.
FUNK = dict(
    name="Funk Automático",
    author="Coletivo Fictício",
    bank="Banco de Teste",
    tags=[("Amplifiers", "Plex"), ("Genres", "Funk & Soul"), ("Characters", "Crunch"), ("Input Sources", "Guitar")],
    components=["AutoFilter", "Stomp Compressor", "Plex", "Tube Compressor", "Phaser Nine",
                "PsycheDelay", "Studio Reverb"],
)


def soundinfo_xml(name: str, author: str, bank: str, tags: list[tuple[str, ...]]) -> str:
    # Como nos arquivos reais, cada caminho de tag vem com todos os seus prefixos.
    paths: list[tuple[str, ...]] = []
    for tag in tags:
        for i in range(1, len(tag) + 1):
            if tag[:i] not in paths:
                paths.append(tag[:i])
    attributes = "".join(
        f"<attribute><value>{escape(p[-1])}</value><user-set>RP://{escape(chr(9).join(p))}</user-set></attribute>"
        for p in paths)
    return (f'<soundinfo version="400"><properties><name>{escape(name)}</name><author>{escape(author)}</author>'
            f"</properties><banks><bank>{escape(bank)}</bank></banks><attributes>{attributes}</attributes></soundinfo>")


def rack_xml(components: list) -> str:
    """Cada componente é um nome (ligado) ou (nome, ligado)."""
    parts = []
    for i, comp in enumerate(components):
        name, on = comp if isinstance(comp, tuple) else (comp, True)
        parts.append(f'<component name="{escape(name)}" uuid="id{i}"><component-audio><parameters>'
                     f'<parameter id="Pwr" value="{1.0 if on else 0.0:.6f}"/></parameters></component-audio></component>')
    return (f'<gr-instrument-chunk time="Sat Oct 25 21:00:00 2026"><gr-rack><non-fix-components>{"".join(parts)}'
            "</non-fix-components></gr-rack></gr-instrument-chunk>")


def tle(preset: dict = RIFF) -> bytes:
    """Um LastEditBuffer.tle: blocos zlib b"atad" ver tipo-invertido b"bilz" tam-comprimido tam-original."""
    blocks = [
        ("info", soundinfo_xml(preset["name"], preset["author"], preset["bank"], preset["tags"])),
        ("prst", rack_xml(preset["components"])),
        ("guis", f'<user_state><last_loaded_preset value="{escape(preset["uri"])}"/></user_state>'),
    ]
    out = bytearray(b"\x00" * 16)
    for kind, xml in blocks:
        raw = (XML_DECL + xml).encode("utf-8")
        packed = zlib.compress(raw)
        out += b"atad" + struct.pack("<I", 1) + kind[::-1].encode() + b"bilz"
        out += struct.pack("<II", len(packed), len(raw)) + packed
    return bytes(out)


def ngrr(preset: dict = FUNK) -> bytes:
    """Um preset .ngrr: os XMLs aparecem sem compressão, no meio de blocos binários."""
    info = "<guitarrig7-database-info>" + soundinfo_xml(
        preset["name"], preset["author"], preset["bank"], preset["tags"]) + "</guitarrig7-database-info>"
    return (b"\x00" * 12 + b"hsin" + b"\x01" * 24
            + (XML_DECL + info).encode("utf-8") + b"\x00\x02\x00\x00 LMX"
            + (XML_DECL + rack_xml(preset["components"])).encode("utf-8") + b"\x00" * 8)
