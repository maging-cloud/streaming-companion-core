# src/companion_settings/panels/ngword.py
from pathlib import Path
from importlib.resources import files

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QInputDialog, QLabel,
)

from companion_core.ngword import load_ngwords

USER_PATH = Path.home() / ".streaming-companion" / "ngwords_user.txt"
_SEED = str(files("companion_core") / "ngwords.txt")


class NGWordPanel(QWidget):
    def __init__(self, user_words=None):
        """user_words: 初期ユーザーワードリスト（省略時は USER_PATH から読み込む）"""
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("組み込みNGワード（読み取り専用）"))
        self._builtin_list = QListWidget()
        self._builtin_list.setEnabled(False)
        for w in load_ngwords([_SEED]):
            self._builtin_list.addItem(w)
        layout.addWidget(self._builtin_list)

        layout.addWidget(QLabel("ユーザーNGワード"))
        self._user_list = QListWidget()
        if user_words is None:
            user_words = list(load_ngwords([str(USER_PATH)]))
        self._user_words: list[str] = list(user_words)
        for w in self._user_words:
            self._user_list.addItem(w)
        layout.addWidget(self._user_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("追加")
        del_btn = QPushButton("削除")
        add_btn.clicked.connect(self._add_word_dialog)
        del_btn.clicked.connect(self._del_word)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _add_word_dialog(self):
        word, ok = QInputDialog.getText(self, "NGワード追加", "追加するワード:")
        if ok and word.strip():
            self._add_word_direct(word.strip().lower())

    def _add_word_direct(self, word: str):
        """テストから直接呼ぶ追加メソッド。"""
        if word and word not in self._user_words:
            self._user_words.append(word)
            self._user_list.addItem(word)

    def _del_word(self):
        row = self._user_list.currentRow()
        if row >= 0:
            word = self._user_list.takeItem(row).text()
            if word in self._user_words:
                self._user_words.remove(word)

    def get_user_words(self) -> list[str]:
        return list(self._user_words)

    def save_and_get_config(self) -> dict:
        """ユーザーワードをファイルに書き出し、config dict を返す。"""
        USER_PATH.parent.mkdir(parents=True, exist_ok=True)
        USER_PATH.write_text("\n".join(self._user_words), encoding="utf-8")
        return {}
