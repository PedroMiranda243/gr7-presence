import json
import os
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import atualizar  # noqa: E402


def make_zip(path: Path, version: str, files: dict[str, str] | None = None, raw: dict[str, str] | None = None) -> Path:
    """Zip no formato da release: tudo dentro de "GR7 Presence/". `raw` grava nomes sem o prefixo."""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("GR7 Presence/gr7_presence/__init__.py", f'__version__ = "{version}"\n')
        for rel, text in (files or {}).items():
            zf.writestr(f"GR7 Presence/{rel}", text)
        for name, text in (raw or {}).items():
            zf.writestr(name, text)
    return path


class Installation:
    """Uma pasta do programa na versão 1.0.0, com dados de quem usa."""

    def __init__(self, base: Path):
        self.root = base / "programa"
        self.write("gr7_presence/__init__.py", '__version__ = "1.0.0"\n')
        self.write("gr7_presence/app.py", "antigo")
        self.write("dados/config.json", '{"language": "pt"}')
        self.write(".venv/pyvenv.cfg", "home = x")

    def write(self, rel: str, text: str) -> None:
        (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel).write_text(text, encoding="utf-8")

    def read(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    def result(self) -> dict:
        return json.loads(self.read("dados/atualizacao.json"))


class PackageFilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def files(self, **kw):
        with zipfile.ZipFile(make_zip(self.base / "x.zip", "1.1.0", **kw)) as zf:
            return atualizar.package_files(zf, "1.1.0")

    def test_maps_to_paths_inside_the_program(self):
        self.assertEqual(sorted(self.files(files={"tools/x.py": "", "README.md": ""})),
                         ["README.md", "gr7_presence/__init__.py", "tools/x.py"])

    def test_refuses_anything_out_of_place(self):
        for bad in ({"files": {"dados/config.json": "{}"}}, {"files": {"Dados/stats.json": "{}"}},
                    {"files": {".venv/Scripts/python.exe": ""}}, {"files": {"../fora.py": ""}},
                    {"raw": {"fora/da/pasta.py": ""}}, {"files": {"C:/Windows/x.dll": ""}}):
            with self.subTest(bad=bad), self.assertRaises(atualizar.UpdateFailed):
                self.files(**bad)

    def test_refuses_other_version(self):
        with zipfile.ZipFile(make_zip(self.base / "y.zip", "1.0.5")) as zf, self.assertRaises(atualizar.UpdateFailed):
            atualizar.package_files(zf, "1.1.0")


class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.inst = Installation(self.base)
        self.started = []

    def run_update(self, zip_path, installer=lambda root: (0, "ok"), closed=True):
        return atualizar.update(self.inst.root, zip_path, "1.1.0", "1.0.0", 1234, installer=installer,
                                starter=self.started.append, wait=lambda pid, timeout: closed)

    def new_zip(self):
        return make_zip(self.base / "GR7-Presence-1.1.0.zip", "1.1.0",
                        {"gr7_presence/app.py": "novo", "tools/novo.py": "criado na 1.1.0"})

    def test_success(self):
        zip_path = self.new_zip()
        result = self.run_update(zip_path)
        self.assertTrue(result["ok"])
        self.assertIn('"1.1.0"', self.inst.read("gr7_presence/__init__.py"))
        self.assertEqual(self.inst.read("gr7_presence/app.py"), "novo")
        self.assertEqual(self.inst.read("tools/novo.py"), "criado na 1.1.0")
        self.assertEqual(self.inst.read("dados/config.json"), '{"language": "pt"}')   # de quem usa: intacto
        self.assertEqual(self.started, [])          # quem abre o programa é o instalador
        self.assertFalse(zip_path.exists())         # o zip baixado não fica para trás
        self.assertEqual(self.inst.result()["para"], "1.1.0")
        self.assertIn("Pronto", self.inst.read("dados/atualizacao.log"))

    def test_installer_failure_brings_the_old_version_back(self):
        result = self.run_update(self.new_zip(), installer=lambda root: (1, "pip falhou"))
        self.assertFalse(result["ok"])
        self.assertIn("código 1", result["erro"])
        self.assertIn('"1.0.0"', self.inst.read("gr7_presence/__init__.py"))
        self.assertEqual(self.inst.read("gr7_presence/app.py"), "antigo")
        self.assertFalse((self.inst.root / "tools" / "novo.py").exists())   # o que a 1.1.0 criou sai
        self.assertEqual(self.started, [self.inst.root])                    # e a versão antiga reabre
        self.assertFalse(self.inst.result()["ok"])
        self.assertIn("pip falhou", self.inst.read("dados/atualizacao.log"))

    def test_installer_crash_also_rolls_back(self):
        def crash(root):
            raise OSError("powershell não encontrado")
        result = self.run_update(self.new_zip(), installer=crash)
        self.assertFalse(result["ok"])
        self.assertEqual(self.inst.read("gr7_presence/app.py"), "antigo")

    def test_program_still_open_changes_nothing(self):
        result = self.run_update(self.new_zip(), closed=False)
        self.assertFalse(result["ok"])
        self.assertIn("não fechou", result["erro"])
        self.assertEqual(self.inst.read("gr7_presence/app.py"), "antigo")

    def test_bad_zip_changes_nothing(self):
        broken = self.base / "quebrado.zip"
        broken.write_bytes(b"isto nao e um zip")
        self.assertFalse(self.run_update(broken)["ok"])
        malicious = make_zip(self.base / "mal.zip", "1.1.0", {"gr7_presence/app.py": "novo", "dados/stats.json": "{}"})
        self.assertFalse(self.run_update(malicious)["ok"])
        self.assertEqual(self.inst.read("gr7_presence/app.py"), "antigo")
        self.assertFalse((self.inst.root / "dados" / "stats.json").exists())
        self.assertEqual(len(self.started), 2)   # nas duas vezes, o programa antigo volta a abrir


class WaitForExitTest(unittest.TestCase):
    def test_gone_process(self):
        self.assertTrue(atualizar.wait_for_exit(0x7FFFFFF0, timeout=1))

    def test_running_process_times_out(self):
        start = time.monotonic()
        self.assertFalse(atualizar.wait_for_exit(os.getpid(), timeout=0.2))
        self.assertLess(time.monotonic() - start, 5)


if __name__ == "__main__":
    unittest.main()
