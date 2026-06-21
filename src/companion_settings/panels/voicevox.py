"""TTS (VOICEVOX) 設定パネル (built-in)。

speaker / base_url を編集する。TTS は generic なので built-in (BPB plugin ではない)。

反映モデル:
  - 編集 (commit) → 起動中の console に **live 反映** (synth を作り直して差し替え、再起動不要)
  - 保存ボタン   → config.toml の [voicevox] に永続化 (headless と共有、次回起動でも有効)
  - 破棄ボタン   → 直近保存時の値にフィールドを戻し、live も元に戻す

apply_cb / persist_cb は注入可能 (テスト用、また console_service が無い設定のみ起動では
apply_cb=None で live 反映を no-op にできる)。
"""
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QVBoxLayout, QHBoxLayout, QSpinBox, QLineEdit,
    QPushButton,
)

from companion_core.sinks.voicevox import DEFAULT_BASE_URL


class VoicevoxPanel(QWidget):
    def __init__(self, cfg, apply_cb=None, persist_cb=None):
        super().__init__()
        self._apply_cb = apply_cb        # callable(new_cfg): 起動中 console へ live 反映
        self._persist_cb = persist_cb    # callable(new_cfg): config.toml [voicevox] へ永続化
        self._baseline = {
            "speaker": int(cfg.get("speaker", 1)),
            "base_url": cfg.get("base_url", DEFAULT_BASE_URL),
        }

        root = QVBoxLayout(self)
        form = QFormLayout()
        self._speaker = QSpinBox()
        self._speaker.setRange(0, 1000)
        self._base_url = QLineEdit()
        form.addRow("Speaker", self._speaker)
        form.addRow("Base URL", self._base_url)
        root.addLayout(form)

        btns = QHBoxLayout()
        self._btn_save = QPushButton("保存")
        self._btn_discard = QPushButton("破棄")
        self._btn_save.clicked.connect(self._on_save)
        self._btn_discard.clicked.connect(self._on_discard)
        btns.addStretch(1)
        btns.addWidget(self._btn_discard)
        btns.addWidget(self._btn_save)
        root.addLayout(btns)

        self._set_fields(self._baseline)
        # commit 時に live 反映 (speaker は値変更、base_url は編集確定)
        self._speaker.valueChanged.connect(self._apply)
        self._base_url.editingFinished.connect(self._apply)

    # ---- 値の出し入れ ----
    def get_config(self) -> dict:
        return {
            "speaker": self._speaker.value(),
            "base_url": self._base_url.text().strip() or DEFAULT_BASE_URL,
        }

    def _set_fields(self, cfg):
        self._speaker.setValue(int(cfg.get("speaker", 1)))
        self._base_url.setText(cfg.get("base_url", DEFAULT_BASE_URL))

    # ---- 反映 / 保存 / 破棄 ----
    def _apply(self):
        if self._apply_cb is not None:
            self._apply_cb(self.get_config())

    def _on_save(self):
        new = self.get_config()
        if self._apply_cb is not None:
            self._apply_cb(new)
        if self._persist_cb is not None:
            self._persist_cb(new)
        self._baseline = new

    def _on_discard(self):
        self._set_fields(self._baseline)
        if self._apply_cb is not None:
            self._apply_cb(dict(self._baseline))
