"""
サンプルプラグイン fixture を使ったエンドツーエンドテスト。
プラグインが companion_core.settings entry-point でUIページを登録する仕組みを確認する。
"""
import unittest

try:
    from PySide6.QtWidgets import QApplication, QWidget
    _app = QApplication.instance() or QApplication([])
    HAS_QT = True
except ImportError:
    HAS_QT = False

from tests.fixtures.sample_plugin import SampleSchemaSettings, SampleWidgetSettings


class TestSampleSchemaPlugin(unittest.TestCase):
    """JSON Schema パス: schema 属性を定義するだけで設定フォームが生成される。"""

    def setUp(self):
        self.panel = SampleSchemaSettings()

    def test_duck_typing_protocol(self):
        """section_id / label / schema が揃っていれば companion-settings が受け入れる。"""
        self.assertTrue(hasattr(self.panel, "section_id"))
        self.assertTrue(hasattr(self.panel, "label"))
        self.assertTrue(hasattr(self.panel, "schema"))
        self.assertNotEqual(self.panel.section_id, "")

    def test_schema_shape(self):
        schema = self.panel.schema
        self.assertEqual(schema.get("type"), "object")
        self.assertIsInstance(schema.get("properties"), dict)

    @unittest.skipUnless(HAS_QT, "PySide6 not installed")
    def test_schema_form_roundtrip(self):
        """build_form でフォームを生成し、値の set/get が正しく動く。"""
        from companion_settings.schema_ui import build_form
        _, get_values, set_values = build_form(self.panel.schema)
        set_values({"difficulty": "hard", "volume": 80})
        result = get_values()
        self.assertEqual(result["difficulty"], "hard")
        self.assertAlmostEqual(result["volume"], 80.0)

    @unittest.skipUnless(HAS_QT, "PySide6 not installed")
    def test_tab_appears_when_enabled(self):
        """plugins.enabled に section_id が含まれていればタブが追加される。"""
        from companion_settings.window import MainWindow
        win = MainWindow(
            cfg={"plugins": {"enabled": ["sample"]}},
            extra_panels=[self.panel],
        )
        labels = [win._tabs.tabText(i) for i in range(win._tabs.count())]
        self.assertTrue(any("サンプル設定" in l for l in labels))

    @unittest.skipUnless(HAS_QT, "PySide6 not installed")
    def test_tab_hidden_when_disabled(self):
        """plugins.enabled に含まれていなければタブは追加されない。"""
        from companion_settings.window import MainWindow
        win = MainWindow(cfg={}, extra_panels=[self.panel])
        labels = [win._tabs.tabText(i) for i in range(win._tabs.count())]
        self.assertFalse(any("サンプル設定" in l for l in labels))

    @unittest.skipUnless(HAS_QT, "PySide6 not installed")
    def test_config_saved_to_section(self):
        """OK 時に section_id をキーとして設定が保存される。"""
        import tempfile, pathlib
        from companion_settings.window import MainWindow
        from companion_settings.config import load

        with tempfile.TemporaryDirectory() as d:
            cfg_path = pathlib.Path(d) / "config.toml"

            # companion_settings.config のデフォルトパスを差し替えるため
            # window を直接テストせず registry モックで検証
            from companion_settings import config as cfg_mod
            orig = cfg_mod.DEFAULT_PATH
            cfg_mod.DEFAULT_PATH = cfg_path
            try:
                win = MainWindow(
                    cfg={"plugins": {"enabled": ["sample"]}},
                    extra_panels=[self.panel],
                )
                # _on_ok を直接呼ぶとメッセージボックスが出るので保存ロジックだけ抽出
                import unittest.mock as mock
                with mock.patch("companion_settings.window.QMessageBox.information"):
                    win._on_ok()
                result = load(cfg_path)
            finally:
                cfg_mod.DEFAULT_PATH = orig

        self.assertIn("sample", result)


@unittest.skipUnless(HAS_QT, "PySide6 not installed")
class TestSampleWidgetPlugin(unittest.TestCase):
    """QWidget パス: build_widget / get_config を自前実装するケース。"""

    def setUp(self):
        self.panel = SampleWidgetSettings()

    def test_duck_typing_protocol(self):
        self.assertTrue(hasattr(self.panel, "section_id"))
        self.assertTrue(hasattr(self.panel, "label"))
        self.assertTrue(callable(getattr(self.panel, "build_widget", None)))
        self.assertTrue(callable(getattr(self.panel, "get_config", None)))

    def test_build_widget_returns_qwidget(self):
        widget = self.panel.build_widget({"greeting": "こんにちは"})
        self.assertIsInstance(widget, QWidget)

    def test_get_config_roundtrip(self):
        self.panel.build_widget({"greeting": "テスト"})
        result = self.panel.get_config()
        self.assertEqual(result["greeting"], "テスト")

    def test_tab_appears_when_enabled(self):
        from companion_settings.window import MainWindow
        win = MainWindow(
            cfg={"plugins": {"enabled": ["sample_widget"]}},
            extra_panels=[self.panel],
        )
        labels = [win._tabs.tabText(i) for i in range(win._tabs.count())]
        self.assertTrue(any("サンプル (カスタムUI)" in l for l in labels))


if __name__ == "__main__":
    unittest.main()
