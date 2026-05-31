import pathlib
import tempfile
import unittest

try:
    import tomli_w  # noqa: F401
    HAS_TOMLI_W = True
except ImportError:
    HAS_TOMLI_W = False


class TestSettingsConfig(unittest.TestCase):
    def test_load_missing_returns_empty(self):
        from companion_settings.config import load
        self.assertEqual(load("/nonexistent/config.toml"), {})

    @unittest.skipUnless(HAS_TOMLI_W, "tomli_w not installed")
    def test_save_creates_file(self):
        from companion_settings.config import save
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "config.toml"
            save({"llm": {"model": "gpt-4"}}, path)
            self.assertTrue(path.exists())

    @unittest.skipUnless(HAS_TOMLI_W, "tomli_w not installed")
    def test_save_and_load_roundtrip(self):
        from companion_settings.config import load, save
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "config.toml"
            data = {
                "llm": {"base_url": "http://test", "model": "gpt-4", "api_key": ""},
                "plugins": {"enabled": ["shop"]},
            }
            save(data, path)
            result = load(path)
        self.assertEqual(result["llm"]["model"], "gpt-4")
        self.assertEqual(result["plugins"]["enabled"], ["shop"])

    @unittest.skipUnless(HAS_TOMLI_W, "tomli_w not installed")
    def test_save_creates_parent_dirs(self):
        from companion_settings.config import save
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "nested" / "config.toml"
            save({"llm": {"model": "x"}}, path)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
