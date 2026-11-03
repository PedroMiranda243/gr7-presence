import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gr7_presence.app import PresenceApp
from gr7_presence.config import DEFAULTS
from gr7_presence.gr7_state import PresetReader
from gr7_presence.preset_library import PresetLibrary
from gr7_presence.stats import Stats
from gr7_presence.tray import TrayUI
from gr7_presence.updates import Release, UpdateChecker


class FakeConfig(dict):
    def __getitem__(self, key):
        return self.get(key, DEFAULTS.get(key))


class NotificationTest(unittest.TestCase):
    """O pystray põe o ícone na bandeja um instante depois de abrir; notificação antes disso some."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        app = PresenceApp(FakeConfig(copy.deepcopy(DEFAULTS)), Stats(base / "s.json"), PresetReader(base / "x.tle"),
                          PresetLibrary(base, extra_dirs=[]), live_state_path=base / "l.json",
                          updates=UpdateChecker("1.2.0", fetch=lambda: None))
        self.ui = TrayUI(app)
        self.addCleanup(self.ui.root.destroy)
        self.ui.icon = mock.Mock(visible=False)

    def test_waits_for_the_icon(self):
        self.ui.app.on_update(Release("1.3.0", "https://exemplo"))
        self.ui._drain()
        self.ui.icon.notify.assert_not_called()
        self.ui.icon.update_menu.assert_called()   # o item do menu não espera nada

        self.ui.icon.visible = True
        self.ui._drain()
        self.ui.icon.notify.assert_called_once()
        self.assertIn("1.3.0", self.ui.icon.notify.call_args.args[1])
        self.ui._drain()
        self.ui.icon.notify.assert_called_once()   # e só uma vez

    def test_release_found_before_the_tray_existed(self):
        app = self.ui.app
        app.updates.available = Release("1.3.0", "https://exemplo")   # achada antes da bandeja
        ui = TrayUI(app)
        self.addCleanup(ui.root.destroy)
        ui.icon = mock.Mock(visible=True)
        ui._drain()
        ui.icon.notify.assert_called_once()
        self.assertIn("1.3.0", ui.icon.notify.call_args.args[1])

    def test_update_result_also_waits(self):
        with mock.patch("gr7_presence.tray.updates.pop_last_result", return_value={"ok": True, "para": "1.3.0"}):
            self.ui._announce_last_update()
        self.ui.icon.notify.assert_not_called()
        self.ui.icon.visible = True
        self.ui._drain()
        self.assertIn("1.3.0", self.ui.icon.notify.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
