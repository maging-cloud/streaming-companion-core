from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QHBoxLayout, QPushButton, QLabel,
)


class PluginsPanel(QWidget):
    def __init__(self, enabled: list[str], all_kinds: list[str]):
        """enabled: 有効な kind 一覧、all_kinds: 検出された全 kind 一覧"""
        super().__init__()
        self._enabled: set[str] = set(enabled)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("インストール済みプラグイン"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)

        self._toggles: dict[str, QPushButton] = {}
        for kind in all_kinds:
            row = QHBoxLayout()
            row.addWidget(QLabel(kind))
            row.addStretch()
            btn = QPushButton("有効" if kind in self._enabled else "無効")
            btn.setCheckable(True)
            btn.setChecked(kind in self._enabled)
            btn.clicked.connect(lambda checked, k=kind: self._set_enabled(k, checked))
            row.addWidget(btn)
            inner_layout.addLayout(row)
            self._toggles[kind] = btn

        inner_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        layout.addWidget(QLabel("変更は再起動後に反映されます"))

    def _set_enabled(self, kind: str, enabled: bool):
        if enabled:
            self._enabled.add(kind)
        else:
            self._enabled.discard(kind)
        btn = self._toggles.get(kind)
        if btn:
            btn.setText("有効" if enabled else "無効")
            btn.setChecked(enabled)

    def get_config(self) -> dict:
        return {"enabled": sorted(self._enabled)}
