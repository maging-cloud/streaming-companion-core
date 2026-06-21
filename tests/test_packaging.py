"""packaging ガード: console の静的アセットが source に存在し import 時に解決できること。

wheel への同梱検証は CI の build ジョブ (scripts/check_wheel.py) が担う。本テストは
source 側でアセットが消えていないこと (backend._STATIC が実ファイルを指すこと) を
高速な単体テストとして保証する。
"""
import unittest

import companion_settings.console.backend as backend


class TestPackaging(unittest.TestCase):
    def test_console_static_index_present(self):
        index = backend._STATIC / "index.html"
        self.assertTrue(index.exists(), f"missing console 静的アセット: {index}")

    def test_index_is_html(self):
        index = backend._STATIC / "index.html"
        self.assertIn("<html", index.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
