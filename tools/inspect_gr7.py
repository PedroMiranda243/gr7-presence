"""Mostra o que o GR7 Presence está lendo agora (preset salvo, preset na tela, Tape Deck).

    .venv\\Scripts\\python tools\\inspect_gr7.py [caminho do LastEditBuffer.tle]
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gr7_presence.detector import Detector, file_version  # noqa: E402
from gr7_presence.gr7_state import DEFAULT_BUFFER_PATH, PresetReader  # noqa: E402
from gr7_presence.live import LivePresetReader, loaded_tracks, main_window, set_dpi_aware  # noqa: E402
from gr7_presence.preset_library import PresetLibrary  # noqa: E402


def show(info) -> None:
    for key, value in info.__dict__.items():
        if value not in (None, [], ""):
            print(f"  {key:14} {value}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    set_dpi_aware()
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BUFFER_PATH
    reader = PresetReader(path)
    info = reader.read()
    mtime = reader.mtime()
    print(f"LastEditBuffer: {path}")
    print(f"  gravado em    {datetime.fromtimestamp(mtime):%d/%m/%Y %H:%M:%S}" if mtime else "  (não existe)")
    if info:
        show(info)

    library = PresetLibrary()
    print(f"\nBiblioteca: {len(library.index)} presets")

    target = Detector().find()
    print("\nProcesso:", target or "Guitar Rig 7 não está aberto")
    if target and target.kind == "standalone":
        print("  versão:", file_version(target.exe))
        print("  janela:", main_window(target.pid))
        live = LivePresetReader(library)
        reading = live.read(target.pid)
        name = reading.name if reading else None
        print("\nPreset na tela (OCR):", name or "não deu para ler (janela minimizada?)")
        if reading and reading.rack_empty is not None:
            print("Rack vazio:", "sim" if reading.rack_empty else "não")
        if name and library.load(name):
            show(library.load(name))
        print("\nTape Deck:", loaded_tracks(target.pid) or "nenhuma faixa aberta")


if __name__ == "__main__":
    main()
