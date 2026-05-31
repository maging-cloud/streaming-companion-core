# Settings UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `companion_settings` パッケージを新設し、PySide6 製のタブ型設定GUIアプリを実装する。プラグインが entry-point 経由で設定タブを追加できる。

**Architecture:** `companion_core.config` で `~/.streaming-companion/config.toml` を読む関数を追加し、dependency-zero を維持する。`companion_settings` は optional extra `[ui]` として同リポジトリに同居し、PySide6 と tomli-w に依存する。起動は `companion-settings` コマンドまたは `python -m companion_settings`。

**Tech Stack:** Python 3.11+, PySide6 >= 6.7, tomli-w >= 1.0, tomllib (stdlib)

---

## ファイルマップ

| 操作 | パス | 役割 |
|---|---|---|
| 新規 | `src/companion_core/config.py` | `config.toml` 読み込み（tomllib、外部依存なし） |
| 修正 | `src/companion_core/llm.py` | `make_client_from_config` を追加 |
| 修正 | `pyproject.toml` | ui extra、scripts、hatch packages を追加 |
| 新規 | `src/companion_settings/__init__.py` | 空 |
| 新規 | `src/companion_settings/__main__.py` | `main()` エントリーポイント |
| 新規 | `src/companion_settings/config.py` | `load()` / `save()` — config.toml 読み書き |
| 新規 | `src/companion_settings/registry.py` | `discover_settings_panels()` / `discover_handler_kinds()` |
| 新規 | `src/companion_settings/schema_ui.py` | JSON Schema → QWidget 自動生成 |
| 新規 | `src/companion_settings/panels/__init__.py` | 空 |
| 新規 | `src/companion_settings/panels/llm.py` | LLM設定パネル |
| 新規 | `src/companion_settings/panels/ngword.py` | NGワード管理パネル |
| 新規 | `src/companion_settings/panels/plugins.py` | プラグイン有効化パネル |
| 新規 | `src/companion_settings/window.py` | `MainWindow` — タブUI + OK/キャンセル |
| 新規 | `tests/test_core_config.py` | companion_core.config のユニットテスト |
| 新規 | `tests/test_settings_config.py` | companion_settings.config のユニットテスト |
| 新規 | `tests/test_settings_registry.py` | registry のユニットテスト |
| 新規 | `tests/test_settings_panels.py` | Qt パネルの基本動作テスト |
| 修正 | `tests/test_boundary.py` | `companion_settings` を FORBIDDEN に追加 |

---

## Task 1: companion_core.config — config.toml リーダー

**Files:**
- Create: `src/companion_core/config.py`
- Create: `tests/test_core_config.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_core_config.py
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m unittest tests.test_core_config
```

期待結果: `ModuleNotFoundError: No module named 'companion_core.config'`

- [ ] **Step 3: companion_core/config.py を実装する**

```python
# src/companion_core/config.py
import tomllib
from pathlib import Path

DEFAULT_PATH = Path.home() / ".streaming-companion" / "config.toml"


def load_config(path=None):
    """config.toml を読み込む。ファイルがなければ空 dict を返す。"""
    p = Path(path) if path is not None else DEFAULT_PATH
    if not p.exists():
        return {}
    with open(p, "rb") as f:
        return tomllib.load(f)


def make_client_from_config(cfg):
    """cfg の [llm] セクションから OpenAIClient を生成。未設定なら None。"""
    from .llm import OpenAIClient
    llm = cfg.get("llm", {})
    base = llm.get("base_url")
    model = llm.get("model")
    if base and model:
        return OpenAIClient(base, llm.get("api_key", ""), model)
    return None
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
python -m unittest tests.test_core_config
```

期待結果: `OK (4 tests)`

- [ ] **Step 5: コミット**

```bash
git add src/companion_core/config.py tests/test_core_config.py
git commit -m "feat(core): config.toml リーダーを追加 (tomllib, dependency-zero)"
```

---

## Task 2: pyproject.toml — パッケージ設定を更新する

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: pyproject.toml を編集する**

`pyproject.toml` の内容を以下に置き換える:

```toml
[project]
name = "streaming-companion-core"
version = "0.1.0"
description = "汎用実況コンパニオン基盤 (ゲーム非依存)"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "Akiyuki Takahashi" }]
dependencies = []

[project.optional-dependencies]
ui = ["PySide6>=6.7", "tomli-w>=1.0"]

[project.scripts]
companion-settings = "companion_settings.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/companion_core", "src/companion_settings"]
```

- [ ] **Step 2: ui extra をインストールする**

```bash
uv pip install -e ".[ui]"
```

期待結果: PySide6 と tomli-w がインストールされる（エラーなし）

- [ ] **Step 3: コミット**

```bash
git add pyproject.toml
git commit -m "build: ui optional extra を追加 (PySide6, tomli-w)"
```

---

## Task 3: companion_settings.config — TOML 読み書き

**Files:**
- Create: `src/companion_settings/__init__.py`
- Create: `src/companion_settings/config.py`
- Create: `tests/test_settings_config.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_settings_config.py
import pathlib
import tempfile
import unittest


class TestSettingsConfig(unittest.TestCase):
    def test_load_missing_returns_empty(self):
        from companion_settings.config import load
        self.assertEqual(load("/nonexistent/config.toml"), {})

    def test_save_creates_file(self):
        from companion_settings.config import save
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "config.toml"
            save({"llm": {"model": "gpt-4"}}, path)
            self.assertTrue(path.exists())

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

    def test_save_creates_parent_dirs(self):
        from companion_settings.config import save
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "nested" / "config.toml"
            save({"llm": {"model": "x"}}, path)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m unittest tests.test_settings_config
```

期待結果: `ModuleNotFoundError: No module named 'companion_settings'`

- [ ] **Step 3: パッケージを作成して config.py を実装する**

```python
# src/companion_settings/__init__.py
# (空ファイル)
```

```python
# src/companion_settings/config.py
import tomllib
import tomli_w
from pathlib import Path

DEFAULT_PATH = Path.home() / ".streaming-companion" / "config.toml"


def load(path=None):
    """config.toml を読み込む。ファイルがなければ空 dict を返す。"""
    p = Path(path) if path is not None else DEFAULT_PATH
    if not p.exists():
        return {}
    with open(p, "rb") as f:
        return tomllib.load(f)


def save(cfg: dict, path=None):
    """config.toml に書き込む。親ディレクトリを自動作成する。"""
    p = Path(path) if path is not None else DEFAULT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        tomli_w.dump(cfg, f)
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
python -m unittest tests.test_settings_config
```

期待結果: `OK (4 tests)`

- [ ] **Step 5: コミット**

```bash
git add src/companion_settings/__init__.py src/companion_settings/config.py tests/test_settings_config.py
git commit -m "feat(settings): companion_settings パッケージ新設 + config TOML 読み書き"
```

---

## Task 4: companion_settings.registry — entry-point 検索

**Files:**
- Create: `src/companion_settings/registry.py`
- Create: `tests/test_settings_registry.py`

- [ ] **Step 1: テストを書く**

```python
# tests/test_settings_registry.py
import unittest
from unittest.mock import MagicMock, patch


class TestDiscoverSettingsPanels(unittest.TestCase):
    def test_returns_empty_when_no_entry_points(self):
        from companion_settings.registry import discover_settings_panels
        with patch("importlib.metadata.entry_points", return_value=[]):
            panels = discover_settings_panels()
        self.assertEqual(panels, [])

    def test_returns_instantiated_panel(self):
        from companion_settings.registry import discover_settings_panels

        class FakePanel:
            section_id = "fake"
            label = "Fake"

        ep = MagicMock()
        ep.load.return_value = FakePanel
        with patch("importlib.metadata.entry_points", return_value=[ep]):
            panels = discover_settings_panels()
        self.assertEqual(len(panels), 1)
        self.assertEqual(panels[0].section_id, "fake")

    def test_skips_broken_plugin(self):
        from companion_settings.registry import discover_settings_panels

        bad_ep = MagicMock()
        bad_ep.load.side_effect = ImportError("broken")
        with patch("importlib.metadata.entry_points", return_value=[bad_ep]):
            panels = discover_settings_panels()
        self.assertEqual(panels, [])


class TestDiscoverHandlerKinds(unittest.TestCase):
    def test_returns_kind_names(self):
        from companion_settings.registry import discover_handler_kinds

        ep1, ep2 = MagicMock(), MagicMock()
        ep1.name, ep2.name = "shop", "chat"
        with patch("importlib.metadata.entry_points", return_value=[ep1, ep2]):
            kinds = discover_handler_kinds()
        self.assertEqual(sorted(kinds), ["chat", "shop"])

    def test_returns_empty_when_none(self):
        from companion_settings.registry import discover_handler_kinds
        with patch("importlib.metadata.entry_points", return_value=[]):
            self.assertEqual(discover_handler_kinds(), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m unittest tests.test_settings_registry
```

期待結果: `ModuleNotFoundError: No module named 'companion_settings.registry'`

- [ ] **Step 3: registry.py を実装する**

```python
# src/companion_settings/registry.py
import importlib.metadata

_SETTINGS_GROUP = "companion_core.settings"
_HANDLERS_GROUP = "companion_core.handlers"


def discover_settings_panels():
    """companion_core.settings entry-point から設定パネルを検索してインスタンス化する。"""
    panels = []
    for ep in importlib.metadata.entry_points(group=_SETTINGS_GROUP):
        try:
            panels.append(ep.load()())
        except Exception:
            pass
    return panels


def discover_handler_kinds():
    """companion_core.handlers entry-point から kind 名の一覧を返す。"""
    return [ep.name for ep in importlib.metadata.entry_points(group=_HANDLERS_GROUP)]
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
python -m unittest tests.test_settings_registry
```

期待結果: `OK (5 tests)`

- [ ] **Step 5: コミット**

```bash
git add src/companion_settings/registry.py tests/test_settings_registry.py
git commit -m "feat(settings): entry-point plugin 検索 registry を追加"
```

---

## Task 5: companion_settings.schema_ui — JSON Schema → Qt フォーム自動生成

**Files:**
- Create: `src/companion_settings/schema_ui.py`
- Create: `tests/test_settings_panels.py` (Qt テスト基盤を含む)

- [ ] **Step 1: Qt テスト基盤とテストを書く**

```python
# tests/test_settings_panels.py
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m unittest tests.test_settings_panels.TestSchemaUi
```

期待結果: `ModuleNotFoundError: No module named 'companion_settings.schema_ui'`

- [ ] **Step 3: schema_ui.py を実装する**

```python
# src/companion_settings/schema_ui.py
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
)


def _make_field(field_schema: dict):
    ftype = field_schema.get("type", "string")
    enum = field_schema.get("enum")
    if enum:
        w = QComboBox()
        w.addItems([str(e) for e in enum])
        return w
    if ftype == "number":
        w = QDoubleSpinBox()
        w.setMinimum(field_schema.get("minimum", 0.0))
        w.setMaximum(field_schema.get("maximum", 9999.0))
        return w
    if ftype == "integer":
        w = QSpinBox()
        w.setMinimum(int(field_schema.get("minimum", 0)))
        w.setMaximum(int(field_schema.get("maximum", 9999)))
        return w
    return QLineEdit()


def build_form(schema: dict):
    """JSON Schema から (QWidget, get_values, set_values) を返す。

    get_values() -> dict  : 現在の入力値を返す
    set_values(dict)      : フォームに値を流し込む
    """
    container = QWidget()
    layout = QFormLayout(container)
    fields: dict[str, QWidget] = {}

    for key, field in schema.get("properties", {}).items():
        title = field.get("title", key)
        widget = _make_field(field)
        layout.addRow(title, widget)
        fields[key] = widget

    def get_values() -> dict:
        result = {}
        for k, w in fields.items():
            if isinstance(w, QComboBox):
                result[k] = w.currentText()
            elif isinstance(w, (QDoubleSpinBox, QSpinBox)):
                result[k] = w.value()
            else:
                result[k] = w.text()
        return result

    def set_values(values: dict) -> None:
        for k, w in fields.items():
            v = values.get(k)
            if v is None:
                continue
            if isinstance(w, QComboBox):
                idx = w.findText(str(v))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            elif isinstance(w, (QDoubleSpinBox, QSpinBox)):
                w.setValue(v)
            else:
                w.setText(str(v))

    return container, get_values, set_values
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
python -m unittest tests.test_settings_panels.TestSchemaUi
```

期待結果: `OK (4 tests)`

- [ ] **Step 5: コミット**

```bash
git add src/companion_settings/schema_ui.py tests/test_settings_panels.py
git commit -m "feat(settings): JSON Schema → Qt フォーム自動生成 (schema_ui)"
```

---

## Task 6: panels/llm.py — LLM設定パネル

**Files:**
- Create: `src/companion_settings/panels/__init__.py`
- Create: `src/companion_settings/panels/llm.py`
- Modify: `tests/test_settings_panels.py`

- [ ] **Step 1: テストを追加する (`tests/test_settings_panels.py` 末尾に追記)**

```python
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m unittest tests.test_settings_panels.TestLLMPanel
```

期待結果: `ModuleNotFoundError: No module named 'companion_settings.panels'`

- [ ] **Step 3: panels/__init__.py と panels/llm.py を実装する**

```python
# src/companion_settings/panels/__init__.py
# (空ファイル)
```

```python
# src/companion_settings/panels/llm.py
from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit


class LLMPanel(QWidget):
    def __init__(self, cfg: dict):
        super().__init__()
        layout = QFormLayout(self)
        self._base_url = QLineEdit(cfg.get("base_url", ""))
        self._api_key = QLineEdit(cfg.get("api_key", ""))
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._model = QLineEdit(cfg.get("model", ""))
        layout.addRow("Base URL", self._base_url)
        layout.addRow("API Key", self._api_key)
        layout.addRow("Model", self._model)

    def get_config(self) -> dict:
        return {
            "base_url": self._base_url.text().strip(),
            "api_key": self._api_key.text().strip(),
            "model": self._model.text().strip(),
        }
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
python -m unittest tests.test_settings_panels.TestLLMPanel
```

期待結果: `OK (2 tests)`

- [ ] **Step 5: コミット**

```bash
git add src/companion_settings/panels/__init__.py src/companion_settings/panels/llm.py tests/test_settings_panels.py
git commit -m "feat(settings): LLM設定パネルを追加"
```

---

## Task 7: panels/ngword.py — NGワード管理パネル

**Files:**
- Create: `src/companion_settings/panels/ngword.py`
- Modify: `tests/test_settings_panels.py`

- [ ] **Step 1: テストを追加する (`tests/test_settings_panels.py` 末尾に追記)**

```python
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m unittest tests.test_settings_panels.TestNGWordPanel
```

期待結果: `ModuleNotFoundError: No module named 'companion_settings.panels.ngword'`

- [ ] **Step 3: panels/ngword.py を実装する**

```python
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
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
python -m unittest tests.test_settings_panels.TestNGWordPanel
```

期待結果: `OK (3 tests)`

- [ ] **Step 5: コミット**

```bash
git add src/companion_settings/panels/ngword.py tests/test_settings_panels.py
git commit -m "feat(settings): NGワード管理パネルを追加"
```

---

## Task 8: panels/plugins.py — プラグイン有効化パネル

**Files:**
- Create: `src/companion_settings/panels/plugins.py`
- Modify: `tests/test_settings_panels.py`

- [ ] **Step 1: テストを追加する (`tests/test_settings_panels.py` 末尾に追記)**

```python
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m unittest tests.test_settings_panels.TestPluginsPanel
```

期待結果: `ModuleNotFoundError: No module named 'companion_settings.panels.plugins'`

- [ ] **Step 3: panels/plugins.py を実装する**

```python
# src/companion_settings/panels/plugins.py
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
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
python -m unittest tests.test_settings_panels.TestPluginsPanel
```

期待結果: `OK (3 tests)`

- [ ] **Step 5: コミット**

```bash
git add src/companion_settings/panels/plugins.py tests/test_settings_panels.py
git commit -m "feat(settings): プラグイン有効化パネルを追加"
```

---

## Task 9: companion_settings.window — MainWindow

**Files:**
- Create: `src/companion_settings/window.py`
- Modify: `tests/test_settings_panels.py`

- [ ] **Step 1: テストを追加する (`tests/test_settings_panels.py` 末尾に追記)**

```python
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
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
python -m unittest tests.test_settings_panels.TestMainWindow
```

期待結果: `ModuleNotFoundError: No module named 'companion_settings.window'`

- [ ] **Step 3: window.py を実装する**

```python
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
    def __init__(self, cfg=None, extra_panels=None):
        """cfg: 設定 dict（省略時は config.toml から読み込む）
        extra_panels: テスト用パネル注入（省略時は registry から discover）
        """
        super().__init__()
        self.setWindowTitle("companion-settings")
        self.setMinimumSize(640, 480)

        if cfg is None:
            cfg = config.load()
        self._cfg = cfg

        if extra_panels is None:
            extra_panels = discover_settings_panels()
        self._extra_panels = extra_panels

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
        self._tabs.addTab(self._llm, "LLM設定")
        self._tabs.addTab(self._ngword, "NGワード")
        self._tabs.addTab(self._plugins, "プラグイン")

        # プラグインパネル（有効なもののみ）
        enabled_set = set(plugin_cfg.get("enabled", []))
        self._panel_widgets: dict[str, tuple] = {}
        for panel in self._extra_panels:
            if panel.section_id not in enabled_set:
                continue
            panel_cfg = self._cfg.get(panel.section_id, {})
            if hasattr(panel, "build_widget"):
                widget = panel.build_widget(panel_cfg)
                panel._get_config = panel.get_config
            else:
                widget, get_values, set_values = build_form(panel.schema)
                set_values(panel_cfg)
                panel._get_config = get_values
            tab_label = f"{getattr(panel, 'icon', '')} {panel.label}".strip()
            self._tabs.addTab(widget, tab_label)
            self._panel_widgets[panel.section_id] = panel

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

        for sid, panel in self._panel_widgets.items():
            new_cfg[sid] = panel._get_config()

        config.save(new_cfg)
        QMessageBox.information(
            self,
            "保存完了",
            "変更を適用するには companion を再起動してください。",
        )
        self.close()
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
python -m unittest tests.test_settings_panels.TestMainWindow
```

期待結果: `OK (3 tests)`

- [ ] **Step 5: コミット**

```bash
git add src/companion_settings/window.py tests/test_settings_panels.py
git commit -m "feat(settings): MainWindow（タブUI + OK/キャンセル）を追加"
```

---

## Task 10: __main__.py + boundary ガード更新

**Files:**
- Create: `src/companion_settings/__main__.py`
- Modify: `tests/test_boundary.py`

- [ ] **Step 1: __main__.py を作成する**

```python
# src/companion_settings/__main__.py
import sys


def main():
    from PySide6.QtWidgets import QApplication
    from companion_settings.window import MainWindow
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: test_boundary.py の FORBIDDEN を更新する**

`tests/test_boundary.py` の FORBIDDEN タプルに `"companion_settings"` を追加する:

```python
FORBIDDEN = ("commenter", "scorer", "evaluator", "tools",
             "llm_match", "shop_handler", "recommendation",
             "companion_settings")
```

- [ ] **Step 3: boundary テストが通ることを確認する**

```bash
python -m unittest tests.test_boundary
```

期待結果: `OK (1 test)`

- [ ] **Step 4: 全テストを実行する**

```bash
python -m unittest discover -s tests -p "test_*.py"
```

期待結果: 全テストが PASS（Qt テストは PySide6 がインストールされていれば実行される）

- [ ] **Step 5: コマンドを確認する**

```bash
companion-settings --help 2>&1 || python -m companion_settings &
sleep 2
kill %1
echo "起動確認OK"
```

期待結果: GUI が起動してすぐに閉じる（エラーなし）

- [ ] **Step 6: コミット**

```bash
git add src/companion_settings/__main__.py tests/test_boundary.py
git commit -m "feat(settings): エントリーポイントを追加 + boundary ガードを更新"
```

---

## 完了確認

全 Task が終わったら以下を実行して最終確認:

```bash
# 全テスト
python -m unittest discover -s tests -p "test_*.py"

# パッケージ確認
pip show streaming-companion-core

# GUI 起動確認（手動で閉じる）
companion-settings
```
