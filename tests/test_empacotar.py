import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import empacotar  # noqa: E402

from gr7_presence import ui_kit  # noqa: E402


class PackageFilesTest(unittest.TestCase):
    """O zip leva tudo o que o programa lê da pasta assets: a 1.4.0 saiu sem a fonte Archivo."""

    def test_every_tracked_asset_goes_into_the_zip(self):
        files = empacotar.tracked()
        assets = [f for f in files if f.startswith("assets/")]
        self.assertTrue(assets)
        chosen = empacotar.package_files(files)
        self.assertEqual([f for f in assets if f not in chosen], [])   # o que não vai no zip sai de assets/

    def test_the_font_goes_with_its_license(self):
        chosen = empacotar.package_files(empacotar.tracked())
        self.assertIn(ui_kit.ARCHIVO.relative_to(empacotar.ROOT).as_posix(), chosen)
        self.assertIn("assets/fonts/OFL.txt", chosen)


if __name__ == "__main__":
    unittest.main()
