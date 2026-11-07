import copy
import hashlib
import io
import json
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from gr7_presence import updates
from gr7_presence.app import PresenceApp
from gr7_presence.config import DEFAULTS
from gr7_presence.gr7_state import PresetReader
from gr7_presence.preset_library import PresetLibrary
from gr7_presence.stats import Stats
from gr7_presence.update_page import note_sections
from gr7_presence.updates import (CHECK_EVERY, Release, UpdateChecker, UpdateError, download, fetch_latest, is_newer,
                                  parse_version, pop_last_result)

ZIP_URL = updates.DOWNLOAD_PREFIX + "v1.1.0/GR7-Presence.zip"


def opener_returning(payload):
    def opener(request, timeout):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return io.BytesIO(body)
    return opener


class VersionTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(parse_version("10.0.1"), (10, 0, 1))
        self.assertIsNone(parse_version("v1.2"))
        self.assertIsNone(parse_version("v1.2.3-beta"))
        self.assertIsNone(parse_version(""))

    def test_newer(self):
        self.assertTrue(is_newer("1.0.1", "1.0.0"))
        self.assertTrue(is_newer("1.10.0", "1.9.9"))   # compara números, não texto
        self.assertFalse(is_newer("1.0.0", "1.0.0"))
        self.assertFalse(is_newer("0.9.0", "1.0.0"))
        self.assertFalse(is_newer("lixo", "1.0.0"))


class FetchTest(unittest.TestCase):
    def test_latest_release(self):
        release = fetch_latest(opener_returning({"tag_name": "v1.2.0", "html_url": "https://github.com/x/y/releases/tag/v1.2.0"}))
        self.assertEqual(release, Release("1.2.0", "https://github.com/x/y/releases/tag/v1.2.0"))

    def test_ignores_drafts_prereleases_and_odd_tags(self):
        self.assertIsNone(fetch_latest(opener_returning({"tag_name": "v2.0.0", "prerelease": True})))
        self.assertIsNone(fetch_latest(opener_returning({"tag_name": "v2.0.0", "draft": True})))
        self.assertIsNone(fetch_latest(opener_returning({"tag_name": "teste"})))
        self.assertIsNone(fetch_latest(opener_returning([1, 2])))

    def test_zip_and_checksum_from_the_release(self):
        release = fetch_latest(opener_returning({
            "tag_name": "v1.1.0", "html_url": "https://github.com/x/y/releases/tag/v1.1.0", "body": "### Novidades",
            "assets": [{"name": "outro.txt", "browser_download_url": "https://x/outro.txt", "digest": "sha256:00"},
                       {"name": "GR7-Presence.zip", "browser_download_url": ZIP_URL, "digest": "sha256:ABC123"}],
        }))
        self.assertEqual((release.zip_url, release.sha256, release.notes), (ZIP_URL, "abc123", "### Novidades"))
        no_zip = fetch_latest(opener_returning({"tag_name": "v1.1.0", "assets": []}))
        self.assertEqual((no_zip.zip_url, no_zip.sha256), (None, None))

    def test_network_problems_are_quiet(self):
        def offline(request, timeout):
            raise urllib.error.URLError("sem internet")
        self.assertIsNone(fetch_latest(offline))
        self.assertIsNone(fetch_latest(opener_returning(b"<html>erro</html>")))


class CheckerTest(unittest.TestCase):
    def setUp(self):
        self.now = 1_000.0
        self.release = Release("1.1.0", "https://exemplo/1.1.0")
        self.checker = UpdateChecker("1.0.0", fetch=lambda: self.release, clock=lambda: self.now)

    def test_once_a_day(self):
        self.assertTrue(self.checker.due())
        self.checker.check()
        self.assertFalse(self.checker.due())
        self.now += CHECK_EVERY
        self.assertTrue(self.checker.due())

    def test_announces_each_version_once(self):
        self.assertEqual(self.checker.check(), self.release)
        self.assertIsNone(self.checker.check())              # mesma versão: sem aviso repetido
        self.assertEqual(self.checker.available, self.release)  # mas o item do menu continua
        self.release = Release("1.2.0", "https://exemplo/1.2.0")
        self.assertEqual(self.checker.check(), self.release)

    def test_same_or_older_is_not_an_update(self):
        self.release = Release("1.0.0", "https://exemplo/1.0.0")
        self.assertIsNone(self.checker.check())
        self.assertIsNone(self.checker.available)


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.content = b"PK zip de mentira" * 1000

    def release(self, **kw):
        base = dict(version="1.1.0", url="https://exemplo", zip_url=ZIP_URL,
                    sha256=hashlib.sha256(self.content).hexdigest())
        base.update(kw)
        return Release(**base)

    def test_checked_download(self):
        path = download(self.release(), self.folder, opener_returning(self.content))
        self.assertEqual(path.read_bytes(), self.content)
        self.assertEqual(path.name, "GR7-Presence-1.1.0.zip")

    def test_mismatch_is_deleted(self):
        with self.assertRaises(UpdateError):
            download(self.release(), self.folder, opener_returning(self.content + b"alterado"))
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_refuses_without_checksum_or_from_elsewhere(self):
        with self.assertRaises(UpdateError):
            download(self.release(sha256=None), self.folder, opener_returning(self.content))
        with self.assertRaises(UpdateError):
            download(self.release(zip_url="https://outro-site.com/GR7-Presence.zip"), self.folder,
                     opener_returning(self.content))

    def test_network_error_leaves_nothing(self):
        def offline(request, timeout):
            raise urllib.error.URLError("caiu")
        with self.assertRaises(UpdateError):
            download(self.release(), self.folder, offline)
        self.assertEqual(list(self.folder.iterdir()), [])


class StartUpdaterTest(unittest.TestCase):
    def test_runs_a_copy_and_waits_for_this_process(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(updates.subprocess, "Popen") as popen:
            folder = Path(tmp)
            updates.start_updater(folder / "GR7-Presence-1.1.0.zip", Release("1.1.0", "u"), current="1.0.0",
                                  project_dir=Path("C:/programa"), python=Path("pythonw.exe"), pid=4321, folder=folder)
            self.assertTrue((folder / "atualizar.py").exists())   # cópia, fora da pasta do programa
            args = popen.call_args.args[0]
            self.assertEqual(args[1], str(folder / "atualizar.py"))
            self.assertEqual(args[args.index("--esperar-pid") + 1], "4321")
            self.assertEqual(args[args.index("--versao") + 1], "1.1.0")
            self.assertEqual(args[args.index("--versao-atual") + 1], "1.0.0")


class LastResultTest(unittest.TestCase):
    def test_read_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "atualizacao.json"
            path.write_text('{"ok": true, "para": "1.1.0"}', encoding="utf-8")
            self.assertEqual(pop_last_result(path), {"ok": True, "para": "1.1.0"})
            self.assertIsNone(pop_last_result(path))   # só avisa uma vez
            path.write_text("lixo", encoding="utf-8")
            self.assertIsNone(pop_last_result(path))


class NotesTest(unittest.TestCase):
    def test_plain_text(self):
        notes = "### Novidades\n- **Aviso** de versão: `check_updates`\n- Outro item"
        self.assertEqual(note_sections(notes), [("Novidades", [("Aviso de versão: check_updates", 0), ("Outro item", 0)])])
        changelog = ("### Como atualizar\n- Pela bandeja\n\n### Mudanças\n- **Painel** novo, com o\n  cartão de agora\n"
                     "  - item de dentro\n")
        self.assertEqual(note_sections(changelog), [("Mudanças", [("Painel novo, com o cartão de agora", 0), ("item de dentro", 1)])])


class FakeConfig(dict):
    def __getitem__(self, key):
        return self.get(key, DEFAULTS.get(key))


class AppTest(unittest.TestCase):
    def make_app(self, **config):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.fetches = 0

        def fetch():
            self.fetches += 1
            return Release("9.0.0", "https://exemplo/9.0.0")

        return PresenceApp(FakeConfig(copy.deepcopy(DEFAULTS), **config), Stats(base / "stats.json"),
                           PresetReader(base / "nao-existe.tle"), PresetLibrary(base, extra_dirs=[]),
                           live_state_path=base / "live_state.json", updates=UpdateChecker("1.0.0", fetch=fetch))

    def test_announces_in_background(self):
        app = self.make_app()
        found = threading.Event()
        app.on_update = lambda release: found.set()
        app._check_updates()
        self.assertTrue(found.wait(5))
        self.assertEqual(app.updates.available.version, "9.0.0")

    def test_can_be_turned_off(self):
        app = self.make_app(check_updates=False)
        app._check_updates()
        self.assertEqual(self.fetches, 0)


if __name__ == "__main__":
    unittest.main()
