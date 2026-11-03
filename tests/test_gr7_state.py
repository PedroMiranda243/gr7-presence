import os
import tempfile
import time
import unittest
from pathlib import Path

from gr7_presence.gr7_state import PresetReader, parse_buffer, read_blocks

from tests import sinteticos


class ParseBufferTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = sinteticos.tle()
        cls.info = parse_buffer(cls.data)

    def test_blocks(self):
        self.assertTrue({"info", "prst", "guis"} <= set(read_blocks(self.data)))

    def test_preset_metadata(self):
        self.assertEqual(self.info.name, "Riff Pesado")
        self.assertEqual(self.info.author, "Autora Fictícia")
        self.assertEqual(self.info.bank, "Banco de Teste")
        self.assertTrue(self.info.is_factory)
        self.assertEqual(self.info.edition, "Guitar Rig 7 Pro")

    def test_tags(self):
        self.assertEqual(self.info.amp, "Van 51")
        self.assertEqual(self.info.genres, ["Metal"])
        self.assertEqual(self.info.fx_types, ["Hi Gain"])
        self.assertEqual(self.info.characters, ["Distorted"])
        self.assertEqual(self.info.input_source, "Guitar")
        self.assertEqual(self.info.tags, ["Metal", "Hi Gain", "Distorted"])

    def test_chain(self):
        # O Delay Man está desligado no rack: não entra na cadeia.
        self.assertEqual(self.info.chain, ["Skreamer", "Van 51", "Control Room Pro", "PsycheDelay", "Vintage Verb"])
        self.assertNotIn("Van 51", self.info.effects)

    def test_garbage_does_not_raise(self):
        self.assertIsNone(parse_buffer(b""))
        self.assertIsNone(parse_buffer(b"\x00" * 100))
        broken = bytearray(self.data)
        rack = self.data.find(b"tsrp")              # tipo "prst" gravado ao contrário
        broken[rack + 30:rack + 70] = b"\x00" * 40   # corrompe o bloco do rack
        info = parse_buffer(bytes(broken))
        self.assertEqual(info.name, "Riff Pesado")
        self.assertEqual(info.chain, [])


class SplitMarkersTest(unittest.TestCase):
    def test_split_markers_are_not_effects(self):
        names = ["Split", "Distortion", "Split B", "Choral", "Split Mix", "CrossOver B", "Bass Pro"]
        rack = "".join(f'<component name="{n}"/>' for n in names)
        xml = f'<?xml version="1.0"?><gr-instrument-chunk><gr-rack><non-fix-components>{rack}</non-fix-components></gr-rack></gr-instrument-chunk>'
        self.assertEqual(parse_buffer(xml.encode()).chain, ["Distortion", "Choral", "Bass Pro"])


class NgrrPresetTest(unittest.TestCase):
    """Presets .ngrr têm os mesmos XMLs, sem compressão."""

    def test_preset_file(self):
        info = parse_buffer(sinteticos.ngrr())
        self.assertEqual(info.name, "Funk Automático")
        self.assertEqual(info.author, "Coletivo Fictício")
        self.assertEqual(info.amp, "Plex")
        self.assertEqual(info.genres, ["Funk & Soul"])
        self.assertEqual(info.chain[:3], ["AutoFilter", "Stomp Compressor", "Plex"])
        self.assertIsNone(info.preset_uri)   # só o .tle tem o user_state


class PresetReaderTest(unittest.TestCase):
    def test_rereads_only_when_mtime_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "LastEditBuffer.tle"
            path.write_bytes(sinteticos.tle())
            reader = PresetReader(path)
            first = reader.read()
            self.assertIs(reader.read(), first)
            time.sleep(0.05)
            path.write_bytes(sinteticos.tle())
            later = path.stat().st_mtime + 5
            os.utime(path, (later, later))
            self.assertIsNot(reader.read(), first)

    def test_missing_file(self):
        self.assertIsNone(PresetReader(Path("Z:/nao/existe.tle")).read())


if __name__ == "__main__":
    unittest.main()
