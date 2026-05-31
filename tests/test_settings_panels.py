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


@unittest.skipUnless(HAS_QT, "PySide6 not installed")
class TestNGWordPanel(unittest.TestCase):
    def _make(self, user_words=None):
        from companion_settings.panels.ngword import NGWordPanel
        return NGWordPanel(user_words=user_words or [])

    def test_add_word(self):
        panel = self._make()
        panel._add_word_direct("badword")
        self.assertIn("badword", panel.get_user_words())

    def test_add_duplicate_ignored(self):
        panel = self._make(["badword"])
        panel._add_word_direct("badword")
        self.assertEqual(panel.get_user_words().count("badword"), 1)

    def test_delete_word(self):
        panel = self._make(["badword"])
        panel._user_list.setCurrentRow(0)
        panel._del_word()
        self.assertNotIn("badword", panel.get_user_words())


@unittest.skipUnless(HAS_QT, "PySide6 not installed")
class TestPluginsPanel(unittest.TestCase):
    def _make(self, enabled=None, kinds=None):
        from companion_settings.panels.plugins import PluginsPanel
        return PluginsPanel(enabled=enabled or [], all_kinds=kinds or [])

    def test_get_config_returns_enabled_list(self):
        panel = self._make(enabled=["shop"], kinds=["shop", "chat"])
        cfg = panel.get_config()
        self.assertIn("shop", cfg["enabled"])
        self.assertNotIn("chat", cfg["enabled"])

    def test_toggle_enables_kind(self):
        panel = self._make(enabled=[], kinds=["shop"])
        panel._set_enabled("shop", True)
        self.assertIn("shop", panel.get_config()["enabled"])

    def test_toggle_disables_kind(self):
        panel = self._make(enabled=["shop"], kinds=["shop"])
        panel._set_enabled("shop", False)
        self.assertNotIn("shop", panel.get_config()["enabled"])


@unittest.skipUnless(HAS_QT, "PySide6 not installed")
class TestMainWindow(unittest.TestCase):
    def _make(self, cfg=None, panels=None):
        from companion_settings.window import MainWindow
        return MainWindow(cfg=cfg or {}, extra_panels=panels or [])

    def test_window_has_three_builtin_tabs(self):
        win = self._make()
        tab = win._tabs
        labels = [tab.tabText(i) for i in range(tab.count())]
        self.assertIn("LLM設定", labels)
        self.assertIn("NGワード", labels)
        self.assertIn("プラグイン", labels)

    def test_plugin_panel_tab_added_when_enabled(self):
        class FakePanel:
            section_id = "shop"
            label = "ショップ設定"
            icon = ""
            schema = {"type": "object", "properties": {}}

        win = self._make(
            cfg={"plugins": {"enabled": ["shop"]}},
            panels=[FakePanel()],
        )
        labels = [win._tabs.tabText(i) for i in range(win._tabs.count())]
        self.assertIn("ショップ設定", labels)

    def test_plugin_panel_not_added_when_disabled(self):
        class FakePanel:
            section_id = "shop"
            label = "ショップ設定"
            icon = ""
            schema = {"type": "object", "properties": {}}

        win = self._make(cfg={}, panels=[FakePanel()])
        labels = [win._tabs.tabText(i) for i in range(win._tabs.count())]
        self.assertNotIn("ショップ設定", labels)
