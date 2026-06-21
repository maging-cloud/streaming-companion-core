"""packaging ガード: 統合 console の主要モジュールが import 可能なこと。

wheel への同梱検証は CI の build ジョブ (scripts/check_wheel.py) が担う。本テストは
source 側で主要モジュールが import できること (移動・削除での欠落) を保証する。
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import PySide6  # noqa: F401
    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False


class TestPackaging(unittest.TestCase):
    def test_core_console_providers_importable(self):
        import companion_core.console_providers as cp
        self.assertTrue(hasattr(cp, "discover_console_providers"))
        self.assertTrue(hasattr(cp, "build_service"))

    @unittest.skipUnless(HAS_PYSIDE6, "PySide6 未インストール")
    def test_settings_ui_importable(self):
        import companion_settings.window as w
        import companion_settings.live_panel as lp
        self.assertTrue(hasattr(w, "MainWindow"))
        self.assertTrue(hasattr(lp, "LivePanel"))


if __name__ == "__main__":
    unittest.main()
