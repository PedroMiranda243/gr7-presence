import tempfile
import unittest
from pathlib import Path

from gr7_presence.assets import AssetResolver
from PIL import Image, ImageDraw

from gr7_presence.live import LivePresetReader, clean_track_name, is_user_track, rack_is_empty
from gr7_presence.preset_library import PresetLibrary

from tests import sinteticos


def write_preset(path: Path) -> None:
    """A biblioteca acha o preset pelo nome do arquivo; o conteúdo é sempre o mesmo preset sintético."""
    path.write_bytes(sinteticos.ngrr())


class FakeOcr:
    available = True


class LibraryAndPickTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        factory = Path(self.tmp.name) / "Rack Presets"
        (factory / "LE").mkdir(parents=True)
        for name in ("Auto Rhythm", "Basic Plex", "RTM2 Power", "Solo Delay 51"):
            write_preset(factory / f"{name}.ngrr")
        write_preset(factory / "LE" / "Basic Plex.ngrr")
        self.library = PresetLibrary(factory, extra_dirs=[])
        self.reader = LivePresetReader(self.library, FakeOcr())

    def tearDown(self):
        self.tmp.cleanup()

    def test_match(self):
        self.assertEqual(self.library.match("Auto Rhythm"), ("Auto Rhythm", 1.0))
        self.assertEqual(self.library.match("auto rhythm *")[0], "Auto Rhythm")
        self.assertEqual(self.library.match("Auto Rhvthm")[0], "Auto Rhythm")   # erro típico de OCR
        self.assertIsNone(self.library.match("Signal Flow"))
        self.assertIsNone(self.library.match("x"))

    def test_shallow_file_wins(self):
        self.assertEqual(self.library.index["basic plex"][1].parent.name, "Rack Presets")

    def test_load_marks_factory(self):
        info = self.library.load("Auto Rhythm")
        self.assertTrue(info.is_factory)
        self.assertEqual(info.amp, "Plex")
        self.assertIsNone(self.library.load("Não existe"))

    def test_user_presets_found_without_restart(self):
        user = Path(self.tmp.name) / "User Content" / "Guitar Rig 7"
        (user / "Rack Presets").mkdir(parents=True)
        library = PresetLibrary(Path(self.tmp.name) / "Rack Presets", extra_dirs=[user])
        library.RESCAN_SECONDS = 0
        self.assertIsNone(library.match("ABCD - Indie Lead 1"))
        write_preset(user / "Rack Presets" / "ABCD - Indie Lead 1.ngrr")
        self.assertEqual(library.match("ABCD - Indie Lead 1")[0], "ABCD - Indie Lead 1")
        self.assertFalse(library.load("ABCD - Indie Lead 1").is_factory)

    def test_truncated_names(self):
        factory = Path(self.tmp.name) / "Rack Presets"
        for name in ("ABCD - Post Punk Lead 6 (Remaster)", "ABCD - Post Punk Lead 2 (Remaster)", "ABCD - Post Punk Lead 6"):
            write_preset(factory / f"{name}.ngrr")
        library = PresetLibrary(factory, extra_dirs=[])
        # como o Guitar Rig mostra e como o OCR leu (espaço sumido, "l" virou "I")
        self.assertEqual(library.match("ABCD- Post Punk Lead 6 (R...")[0], "ABCD - Post Punk Lead 6 (Remaster)")
        self.assertEqual(library.match("ABCD - Post Punk Lead 2 (R…")[0], "ABCD - Post Punk Lead 2 (Remaster)")
        self.assertEqual(library.match("ABCD - Post Punk Lead 6 (R...")[0], "ABCD - Post Punk Lead 6 (Remaster)")
        self.assertEqual(library.match("ABCD- Post Punk Lead 6 (R...")[0], "ABCD - Post Punk Lead 6 (Remaster)")
        self.assertIsNone(library.match("ABCD - Post Punk L..."))   # empate entre vários: não chuta
        self.assertIsNone(library.match("AR..."))                   # curto demais

    def test_pick_topmost_known_preset(self):
        lines = [("CUITAE O", 10, 13), ("Presets", 49, 69), ("Components", 130, 69),
                 ("Auto Rhythm", 356, 68), ("Signal Flow", 1241, 53), ("Basic Plex", 380, 160)]
        self.assertEqual(self.reader.pick(lines), "Auto Rhythm")

    def test_pick_nothing(self):
        self.assertIsNone(self.reader.pick([("Presets", 49, 69), ("Search", 25, 113)]))

    def test_ocr_confusions(self):
        self.assertEqual(self.library.match("Auto Rhyth m")[0], "Auto Rhythm")   # espaço a mais
        self.assertEqual(self.library.match("RTM2 Power")[0], "RTM2 Power")
        self.assertEqual(self.library.match("RTMZ Power")[0], "RTM2 Power")      # fuzzy
        self.assertEqual(self.library.match("Solo DeIay 51")[0], "Solo Delay 51")  # l -> I

    def test_unknown_name_at_known_position(self):
        """Preset fora da biblioteca: vale o texto onde o nome do preset estava antes."""
        self.reader.pick([("Presets", 98, 138), ("Auto Rhythm", 712, 136)])
        lines = [("Presets", 98, 138), ("Meu Timbre Novo", 712, 137), ("Signal Flow", 2482, 106)]
        self.assertEqual(self.reader.pick(lines), "Meu Timbre Novo")

    def test_unknown_name_without_anchor(self):
        self.assertIsNone(self.reader.pick([("Meu Timbre Novo", 712, 137)]))


class RackEmptyTest(unittest.TestCase):
    def window(self, component: bool) -> Image.Image:
        im = Image.new("RGB", (1440, 780), (18, 18, 18))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 1440, 105), fill=(43, 43, 43))          # cabeçalho
        d.text((356, 67), "RTM2 Power", fill=(214, 214, 214))
        if component:
            d.rectangle((350, 300, 1050, 380), fill=(242, 160, 40))  # um componente (laranja)
        return im

    def test_empty_rack(self):
        self.assertTrue(rack_is_empty(self.window(False), 356, 67))

    def test_rack_with_component(self):
        self.assertFalse(rack_is_empty(self.window(True), 356, 67))

    def test_too_small(self):
        self.assertIsNone(rack_is_empty(Image.new("RGB", (300, 200)), 250, 150))


class TrackTest(unittest.TestCase):
    def test_clean_track_name(self):
        cases = {
            "C:/Users/x/Downloads/Banda Ficticia Primeira Cancao Guitar Backing Track woriginal vocals.wav": "Banda Ficticia Primeira Cancao",
            "Banda X - Musica Y (Backing Track).mp3": "Banda X - Musica Y",
            "banda_z_cancao_longa_jam_track_[HQ].wav": "banda z cancao longa",
            "Blues in A 90 BPM.wav": "Blues in A",
        }
        for raw, expected in cases.items():
            self.assertEqual(clean_track_name(raw), expected, raw)
        self.assertIsNone(clean_track_name("backing track.wav"))

    def test_is_user_track(self):
        import os
        temp = os.path.join(os.environ["LOCALAPPDATA"], "Native Instruments", "Guitar Rig 7", "Temp",
                            "TapeDeck 1  Oct 26 00-40-39.wav")
        self.assertFalse(is_user_track(temp))
        self.assertFalse(is_user_track(r"C:\Users\x\Downloads\Tapedeck 2  Oct 12 02-44-34.wav"))
        self.assertFalse(is_user_track(r"C:\Windows\System32\pt-BR\kernel32.dll.mui"))
        self.assertTrue(is_user_track(r"C:\Users\x\Downloads\Banda Ficticia Primeira Cancao.wav"))
        self.assertTrue(is_user_track(r"D:\Musicas\Song.MP3"))


class AssetResolverTest(unittest.TestCase):
    def setUp(self):
        self.resolver = AssetResolver("123")
        self.resolver._fetch = lambda: {"gr7_logo": "900", "tape": "901"}

    def test_keys_by_default(self):
        self.assertEqual(self.resolver.resolve("gr7_logo"), "gr7_logo")

    def test_fallback_when_discord_drops_images(self):
        sent = {"large_image": "gr7_logo", "small_image": "tape"}
        self.assertFalse(self.resolver.needs_fallback(sent, {"large_image": "1", "small_image": "2"}))
        self.assertTrue(self.resolver.needs_fallback(sent, {"large_text": "x"}))
        self.assertEqual(self.resolver.resolve("tape"), "https://cdn.discordapp.com/app-assets/123/901.png")
        self.assertEqual(self.resolver.resolve("desconhecida"), "desconhecida")
        self.assertFalse(self.resolver.needs_fallback(sent, {}))   # já está no plano B
        self.resolver.reset()
        self.assertEqual(self.resolver.resolve("tape"), "tape")


if __name__ == "__main__":
    unittest.main()
