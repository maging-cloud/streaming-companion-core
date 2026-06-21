# src/companion_settings/window.py
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QDialogButtonBox, QMessageBox,
)

from .panels.llm import LLMPanel
from .panels.ngword import NGWordPanel
from .panels.plugins import PluginsPanel
from .registry import discover_settings_panels, discover_handler_kinds
from .schema_ui import build_form
from . import config


class MainWindow(QMainWindow):
    def __init__(self, cfg=None, extra_panels=None, console_service=None):
        """cfg: 設定 dict（省略時は config.toml から読み込む）
        extra_panels: テスト用パネル注入（省略時は registry から discover）
        console_service: ConsoleService。指定時のみ「ライブ」タブを追加する。
        """
        super().__init__()
        self.setWindowTitle("companion-console")
        self.setMinimumSize(640, 480)

        if cfg is None:
            cfg = config.load()
        self._cfg = cfg

        if extra_panels is None:
            extra_panels = discover_settings_panels()
        self._extra_panels = extra_panels

        self._console_service = console_service
        self._live = None

        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        self._tabs = QTabWidget()

        # 組み込みパネル
        all_kinds = discover_handler_kinds()
        plugin_cfg = self._cfg.get("plugins", {})
        self._llm = LLMPanel(self._cfg.get("llm", {}))
        self._ngword = NGWordPanel(user_words=None)
        self._plugins = PluginsPanel(
            enabled=plugin_cfg.get("enabled", []),
            all_kinds=all_kinds,
        )
        # ライブ制御タブ（console_service があるときのみ。設定タブより前に出す）
        if self._console_service is not None:
            from .live_panel import LivePanel
            self._live = LivePanel(self._console_service)
            self._tabs.addTab(self._live, "ライブ")

        self._tabs.addTab(self._llm, "LLM設定")
        self._tabs.addTab(self._ngword, "NGワード")
        self._tabs.addTab(self._plugins, "プラグイン")

        # プラグインパネル（有効なもののみ）
        enabled_set = set(plugin_cfg.get("enabled", []))
        self._panel_getters: dict[str, callable] = {}
        for panel in self._extra_panels:
            if panel.section_id not in enabled_set:
                continue
            panel_cfg = self._cfg.get(panel.section_id, {})
            if hasattr(panel, "build_widget"):
                widget = panel.build_widget(panel_cfg)
                getter = panel.get_config
            else:
                widget, get_values, set_values = build_form(panel.schema)
                set_values(panel_cfg)
                getter = get_values
            tab_label = f"{getattr(panel, 'icon', '')} {panel.label}".strip()
            self._tabs.addTab(widget, tab_label)
            self._panel_getters[panel.section_id] = getter

        root.addWidget(self._tabs)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.close)
        root.addWidget(btns)

    def _on_ok(self):
        new_cfg = dict(self._cfg)
        new_cfg["llm"] = self._llm.get_config()
        new_cfg["plugins"] = self._plugins.get_config()
        self._ngword.save_and_get_config()

        for sid, getter in self._panel_getters.items():
            new_cfg[sid] = getter()

        config.save(new_cfg)
        QMessageBox.information(
            self,
            "保存完了",
            "変更を適用するには companion を再起動してください。",
        )
        self.close()

    def showEvent(self, event):
        super().showEvent(event)
        if self._live is not None:
            self._live.start_pump()

    def closeEvent(self, event):
        if self._live is not None:
            self._live.stop_pump()
        super().closeEvent(event)
