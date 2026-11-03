import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from gr7_presence import app_icon, autostart

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import empacotar  # noqa: E402


class IconFilesTest(unittest.TestCase):
    def test_ico_has_every_taskbar_size(self):
        with Image.open(app_icon.ICO) as ico:
            self.assertEqual(sorted(s[0] for s in ico.info["sizes"]), [16, 20, 24, 32, 40, 48, 64, 128, 256])

    def test_png_for_the_tray(self):
        with Image.open(app_icon.PNG) as png:
            self.assertEqual(png.size, (256, 256))

    def test_icon_goes_in_the_zip(self):
        tracked = [p.replace("*", "x") for p in empacotar.INCLUDE] + ["tests/test_x.py"]
        chosen = empacotar.package_files(tracked)
        self.assertIn("assets/gr7_presence.ico", chosen)
        self.assertIn("assets/gr7_presence.png", chosen)


class TrayImageTest(unittest.TestCase):
    def test_status_dot(self):
        on, off = app_icon.tray_image(True), app_icon.tray_image(False)
        self.assertEqual(on.size, (64, 64))
        self.assertNotEqual(on.getpixel((56, 56)), off.getpixel((56, 56)))   # verde x cinza
        self.assertEqual(on.getpixel((20, 20)), off.getpixel((20, 20)))     # o pedal é o mesmo

    def test_without_the_file(self):
        with mock.patch.object(app_icon, "PNG", Path("Z:/nao/existe.png")):
            image = app_icon.tray_image(False)
        self.assertEqual(image.getpixel((32, 20))[:3], (0xE0, 0x14, 0x1C))   # círculo vermelho


class RefreshShortcutsTest(unittest.TestCase):
    def test_only_existing_shortcuts_are_recreated(self):
        with tempfile.TemporaryDirectory() as tmp:
            menu, startup = Path(tmp) / "menu.lnk", Path(tmp) / "startup.lnk"
            menu.write_bytes(b"atalho antigo")
            created = []
            done = autostart.refresh_shortcuts((menu, startup), create=created.append)
            self.assertEqual(done, [menu])
            self.assertEqual(created, [menu])   # o início com o Windows desligado continua desligado


if __name__ == "__main__":
    unittest.main()
