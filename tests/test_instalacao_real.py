"""Testes contra os arquivos do Guitar Rig 7 instalado neste PC.

Os outros testes usam arquivos sintéticos (tests/sinteticos.py), porque o repositório é público.
Estes conferem que o leitor continua entendendo os arquivos de verdade. Na CI, e em PCs sem o
Guitar Rig 7, ficam pulados.
"""
import unittest

from gr7_presence.gr7_state import DEFAULT_BUFFER_PATH, parse_buffer
from gr7_presence.preset_library import FACTORY_DIR, PresetLibrary


@unittest.skipUnless(FACTORY_DIR.is_dir(), "Guitar Rig 7 não instalado")
class FactoryPresetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = sorted(FACTORY_DIR.rglob("*.ngrr"))

    def test_factory_presets_parse(self):
        self.assertGreater(len(self.files), 100)
        unreadable = []
        for path in self.files:
            info = parse_buffer(path.read_bytes())
            if info is None or not info.name or not info.chain:
                unreadable.append(path.name)
        self.assertLess(len(unreadable), len(self.files) * 0.02, unreadable[:10])

    def test_library_finds_each_preset_by_name(self):
        library = PresetLibrary(FACTORY_DIR, extra_dirs=[])
        sample = self.files[::25]
        misses = [p.stem for p in sample if (library.match(p.stem) or ("",))[0].lower() != p.stem.lower()]
        self.assertEqual(misses, [])


@unittest.skipUnless(DEFAULT_BUFFER_PATH.is_file(), "sem LastEditBuffer.tle neste PC")
class LastEditBufferTest(unittest.TestCase):
    def test_buffer_has_a_preset(self):
        info = parse_buffer(DEFAULT_BUFFER_PATH.read_bytes())
        self.assertIsNotNone(info)
        self.assertTrue(info.name)


if __name__ == "__main__":
    unittest.main()
