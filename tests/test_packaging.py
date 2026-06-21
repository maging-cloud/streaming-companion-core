"""packaging ガード: core lib の主要モジュールが import 可能なこと。

wheel への同梱検証は CI の build ジョブ (scripts/check_wheel.py) が担う。本テストは
source 側で主要モジュールが import できること (移動・削除での欠落) を保証する。
UI (PySide6 console) は別 repo streaming-companion-console へ分離済み。
"""
import unittest


class TestPackaging(unittest.TestCase):
    def test_core_console_providers_importable(self):
        import companion_core.console_providers as cp
        self.assertTrue(hasattr(cp, "discover_console_providers"))
        self.assertTrue(hasattr(cp, "build_service"))

    def test_core_console_logic_importable(self):
        from companion_core.console.service import ConsoleService  # noqa: F401
        from companion_core.console.state import ConsoleState  # noqa: F401
        from companion_core.supervisor import Supervisor  # noqa: F401


if __name__ == "__main__":
    unittest.main()
