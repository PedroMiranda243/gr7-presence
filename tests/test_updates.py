import copy
import io
import json
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path

from gr7_presence.app import PresenceApp
from gr7_presence.config import DEFAULTS
from gr7_presence.gr7_state import PresetReader
from gr7_presence.preset_library import PresetLibrary
from gr7_presence.stats import Stats
from gr7_presence.updates import CHECK_EVERY, Release, UpdateChecker, fetch_latest, is_newer, parse_version


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
