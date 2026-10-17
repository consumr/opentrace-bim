"""Static wiring checks: no IngeTrazo/PySide6 import required."""
from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "OpenTrace_BIM" / "suite_panel.py"
UPDATER = ROOT / "OpenTrace_BIM" / "updater.py"
INIT = ROOT / "OpenTrace_BIM" / "__init__.py"

class UpdateButtonWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = HOME.read_text(encoding="utf-8")
        cls.updater = UPDATER.read_text(encoding="utf-8")

    def test_sources_compile(self):
        for src in (HOME, UPDATER, INIT):
            compile(src.read_bytes(), str(src), "exec")

    def test_button_is_connected(self):
        self.assertIn("self.update_manager = UpdateManager(content)", self.home)
        self.assertIn("self.update_button.clicked.connect(", self.home)
        self.assertIn("self.update_manager.check(manual=True)", self.home)
        self.assertNotIn("self.update_button.setEnabled(False)", self.home)

    def test_opt_in_toggle_is_connected(self):
        self.assertIn("self.auto_update_check.setChecked(auto_check_enabled())", self.home)
        self.assertIn("self.auto_update_check.toggled.connect(self._auto_update_toggled)", self.home)
        self.assertIn("set_auto_check_enabled(bool(enabled))", self.home)
        self.assertIn("if auto_check_enabled() and self.update_manager is not None:", self.home)
        self.assertIn("self.update_manager.check(manual=False)", self.home)
        self.assertNotIn("self.auto_update_check.setEnabled(False)", self.home)

    def test_updater_reads_direct_github_feed_not_ingetrazo(self):
        self.assertIn("api.github.com/repos/lelopes05/opentrace-bim/releases", self.updater)
        self.assertNotIn("ingelibre/ingetrazo-extensions", self.updater)
        self.assertIn("sha256", self.updater)
        self.assertIn("_validate_package", self.updater)

    def test_version_increment(self):
        self.assertIn('__version__ = "0.42.2"', INIT.read_text())

if __name__ == "__main__":
    unittest.main()
