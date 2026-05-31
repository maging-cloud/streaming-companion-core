import pathlib
import tempfile
import unittest

from companion_core.config import load_config, make_client_from_config


class TestLoadConfig(unittest.TestCase):
    def test_missing_file_returns_empty_dict(self):
        self.assertEqual(load_config("/nonexistent/path.toml"), {})

    def test_loads_llm_section(self):
        with tempfile.NamedTemporaryFile(suffix=".toml", mode="wb", delete=False) as f:
            f.write(b'[llm]\nbase_url = "http://localhost"\nmodel = "test"\n')
            path = f.name
        cfg = load_config(path)
        self.assertEqual(cfg["llm"]["base_url"], "http://localhost")
        self.assertEqual(cfg["llm"]["model"], "test")
        pathlib.Path(path).unlink()

    def test_loads_plugins_section(self):
        with tempfile.NamedTemporaryFile(suffix=".toml", mode="wb", delete=False) as f:
            f.write(b'[plugins]\nenabled = ["shop", "chat"]\n')
            path = f.name
        cfg = load_config(path)
        self.assertEqual(cfg["plugins"]["enabled"], ["shop", "chat"])
        pathlib.Path(path).unlink()


class TestMakeClientFromConfig(unittest.TestCase):
    def test_returns_none_when_empty(self):
        self.assertIsNone(make_client_from_config({}))

    def test_returns_none_when_missing_model(self):
        self.assertIsNone(make_client_from_config({"llm": {"base_url": "http://x"}}))

    def test_returns_client_when_configured(self):
        from companion_core.llm import OpenAIClient
        cfg = {"llm": {"base_url": "http://localhost", "model": "gpt-4", "api_key": ""}}
        client = make_client_from_config(cfg)
        self.assertIsInstance(client, OpenAIClient)
        self.assertEqual(client.model, "gpt-4")
        self.assertEqual(client.base_url, "http://localhost")


if __name__ == "__main__":
    unittest.main()
