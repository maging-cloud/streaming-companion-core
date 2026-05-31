import unittest

try:
    from PySide6.QtWidgets import QApplication, QLineEdit, QComboBox, QDoubleSpinBox
    _app = QApplication.instance() or QApplication([])
    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 not installed")
class TestSchemaUi(unittest.TestCase):
    def _build(self, schema, values=None):
        from companion_settings.schema_ui import build_form
        widget, get_values, set_values = build_form(schema)
        if values:
            set_values(values)
        return widget, get_values, set_values

    def test_string_field_creates_lineedit(self):
        schema = {"type": "object", "properties": {"name": {"type": "string", "title": "名前"}}}
        widget, get_values, _ = self._build(schema, {"name": "テスト"})
        self.assertEqual(get_values()["name"], "テスト")

    def test_enum_field_creates_combobox(self):
        schema = {
            "type": "object",
            "properties": {"level": {"type": "string", "title": "難易度", "enum": ["easy", "hard"]}},
        }
        widget, get_values, set_values = self._build(schema)
        set_values({"level": "hard"})
        self.assertEqual(get_values()["level"], "hard")

    def test_number_field_respects_bounds(self):
        schema = {
            "type": "object",
            "properties": {"vol": {"type": "number", "title": "音量", "minimum": 0, "maximum": 100}},
        }
        widget, get_values, set_values = self._build(schema)
        set_values({"vol": 80})
        self.assertAlmostEqual(get_values()["vol"], 80.0)

    def test_unknown_keys_ignored_in_set_values(self):
        schema = {"type": "object", "properties": {"x": {"type": "string", "title": "X"}}}
        widget, get_values, set_values = self._build(schema)
        set_values({"x": "hello", "unknown": "ignored"})
        self.assertEqual(get_values()["x"], "hello")


@unittest.skipUnless(HAS_QT, "PySide6 not installed")
class TestLLMPanel(unittest.TestCase):
    def _make(self, cfg=None):
        from companion_settings.panels.llm import LLMPanel
        return LLMPanel(cfg or {})

    def test_empty_config_renders(self):
        panel = self._make()
        cfg = panel.get_config()
        self.assertEqual(cfg["base_url"], "")
        self.assertEqual(cfg["api_key"], "")
        self.assertEqual(cfg["model"], "")

    def test_preloads_values(self):
        panel = self._make({"base_url": "http://x", "model": "gpt-4", "api_key": "sk"})
        cfg = panel.get_config()
        self.assertEqual(cfg["base_url"], "http://x")
        self.assertEqual(cfg["model"], "gpt-4")
        self.assertEqual(cfg["api_key"], "sk")
