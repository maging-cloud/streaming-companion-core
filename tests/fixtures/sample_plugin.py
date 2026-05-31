"""
サンプルプラグイン設定パネル — テスト用 fixture。

実際のプラグインは以下のパターンで pyproject.toml に entry-point を宣言する:

    [project.entry-points."companion_core.settings"]
    my_plugin = "yourpkg.settings:MyPluginSettings"

    [project.entry-points."companion_core.handlers"]
    my_plugin = "yourpkg.handler:MyHandler"

section_id は companion_core.handlers の kind 名と一致させること。
"""


class SampleSchemaSettings:
    """JSON Schema パス: schema 属性を定義するだけで自動フォーム生成。"""

    section_id = "sample"
    label = "サンプル設定"
    icon = "🎮"

    schema = {
        "type": "object",
        "properties": {
            "difficulty": {
                "type": "string",
                "title": "難易度",
                "enum": ["easy", "normal", "hard"],
            },
            "volume": {
                "type": "number",
                "title": "音量",
                "minimum": 0,
                "maximum": 100,
            },
        },
    }


class SampleWidgetSettings:
    """QWidget パス: build_widget / get_config を自前実装。"""

    section_id = "sample_widget"
    label = "サンプル (カスタムUI)"
    icon = "🔧"

    def build_widget(self, config: dict):
        from PySide6.QtWidgets import QFormLayout, QLineEdit, QWidget
        self._widget = QWidget()
        layout = QFormLayout(self._widget)
        self._greeting = QLineEdit(config.get("greeting", ""))
        layout.addRow("挨拶文", self._greeting)
        return self._widget

    def get_config(self) -> dict:
        return {"greeting": self._greeting.text().strip()}
