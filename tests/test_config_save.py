import os
import tempfile
import unittest

try:
    import tomli_w  # noqa: F401

    HAS_TOMLI_W = True
except ImportError:
    HAS_TOMLI_W = False

from companion_core.config import load_config, save_config


@unittest.skipUnless(HAS_TOMLI_W, "tomli-w 未インストール")
class TestSaveConfig(unittest.TestCase):
    def test_roundtrip(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "config.toml")
        save_config({"console": {"port": 8765}, "speech": {"min_interval": 5.0}}, path)
        cfg = load_config(path)
        self.assertEqual(cfg["console"]["port"], 8765)
        self.assertEqual(cfg["speech"]["min_interval"], 5.0)

    def test_creates_parent_dir(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "nested", "config.toml")
        save_config({"a": {"b": 1}}, path)
        self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
