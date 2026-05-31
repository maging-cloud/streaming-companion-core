# 設定UI 設計仕様

**日付:** 2026-05-31
**対象:** streaming-companion-core

---

## 概要

配信者（エンドユーザー）とプラグイン開発者の両方が使う設定GUIアプリ。  
Windows必須・Mac対応。PySide6 製のスタンドアロンウィンドウアプリとして提供する。

---

## アーキテクチャ

### パッケージ構成

既存の `companion_core` とは**別パッケージ** `companion_settings` を同リポジトリ内に追加する。  
依存は一方向（`companion_settings` → `companion_core`）を維持する。

```
src/
  companion_core/        ← 既存（変更最小限）
    config.py            ← 新設: config.toml 読み込みロジック
  companion_settings/    ← 新設
    __main__.py          ← python -m companion_settings / companion-settings コマンド
    window.py            ← MainWindow（タブUI）
    registry.py          ← entry-point でプラグイン設定パネルを discover
    config.py            ← ~/.streaming-companion/config.toml の読み書き
    schema_ui.py         ← JSON Schema → Qt ウィジェット 自動生成
    panels/
      llm.py             ← LLM設定パネル（組み込み）
      ngword.py          ← NGワード管理パネル（組み込み）
      plugins.py         ← プラグイン有効化パネル（組み込み）
```

### インストール

```toml
# pyproject.toml
[project.optional-dependencies]
ui = ["PySide6>=6.7"]

[project.scripts]
companion-settings = "companion_settings.__main__:main"
```

```bash
pip install streaming-companion-core[ui]
companion-settings          # GUIが開く
python -m companion_settings  # 同上
```

---

## UIレイアウト

**タブ型（Windowsネイティブ風、ライトテーマ）**

```
┌─────────────────────────────────────────────────────┐
│ LLM設定 │ NGワード │ プラグイン │ 🎮 ショップ │ ...  │  ← タブ
├─────────────────────────────────────────────────────┤
│                                                     │
│   各パネルのコンテンツ（ラベル＋入力フォーム）          │
│                                                     │
├─────────────────────────────────────────────────────┤
│                          [キャンセル]  [OK]          │  ← ボタンバー
└─────────────────────────────────────────────────────┘
```

- 組み込みタブ（左側固定）: **LLM設定 / NGワード / プラグイン**
- プラグインタブ（右側に追加）: 有効化したプラグインが追加するタブ
- ウィンドウサイズ: 640×480 以上、リサイズ可

---

## 組み込みパネル詳細

### LLM設定

| フィールド | 型 | 説明 |
|---|---|---|
| Base URL | 文字列 | OpenAI 互換エンドポイント |
| API Key | パスワード入力 | マスク表示、空可 |
| Model | 文字列 | 例: gpt-4o-mini |

### NGワード管理

- 組み込み `ngwords.txt` の語句をグレーアウト・読み取り専用で表示
- ユーザーワード（`~/.streaming-companion/ngwords_user.txt`）は追加・削除可能
- 追加ボタン / 選択して削除ボタン

### プラグイン管理

- entry-point group `companion_core.handlers` から発見したプラグインを一覧表示
- 各プラグインに **有効 / 無効** トグル
- 有効にしたプラグインのみタブに追加される
- プラグインのパッケージ名・バージョンを表示

---

## プラグイン設定 API

プラグインは entry-point group `companion_core.settings` に設定パネルを登録する。

### 簡単パス: JSON Schema

プラグイン作者が Qt を知らなくても設定フォームを追加できる。

```python
# yourpkg/settings.py
class MyHandlerSettings:
    section_id = "my_handler"      # config.toml の [my_handler] セクションキー
    label = "マイハンドラー設定"    # タブに表示される名前
    icon = "🎮"                    # タブのアイコン（省略可）

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
```

`schema_ui.py` が JSON Schema を解析して Qt フォームを自動生成する。

### 高度パス: QWidget を直接返す

```python
class MyHandlerSettings:
    section_id = "my_handler"
    label = "マイハンドラー設定"

    def build_widget(self, config: dict) -> QWidget:
        """起動時に呼ばれる。config は config.toml の [my_handler] セクション。"""
        ...

    def get_config(self) -> dict:
        """OK ボタン押下時に呼ばれる。保存する dict を返す。"""
        ...
```

### entry-point 登録

```toml
# yourpkg/pyproject.toml
[project.entry-points."companion_core.settings"]
my_handler = "yourpkg.settings:MyHandlerSettings"
```

`companion_settings.registry` が起動時に discover し、**有効化されているプラグインのパネルのみ**タブに追加する。

### 簡単パスと高度パスの切り替え

`registry.py` は以下の duck typing で判定する。`schema` 属性が存在すれば JSON Schema パス、`build_widget` メソッドが存在すれば QWidget パスとして処理する。両方定義した場合は `build_widget` を優先する。

### プラグインが登録する entry-point

プラグインパッケージは2つの entry-point group を登録する:

| group | 役割 |
|---|---|
| `companion_core.handlers` | handler クラス（実況生成ロジック）— 既存の仕組み |
| `companion_core.settings` | 設定パネルクラス（UI）— 今回追加、省略可 |

settings entry-point を登録しないプラグインは「プラグイン管理」タブでON/OFFできるが、専用設定タブは追加されない。

---

## 設定ファイル構造

`~/.streaming-companion/config.toml`

```toml
[llm]
base_url = "https://api.openai.com/v1"
api_key  = "sk-..."
model    = "gpt-4o-mini"

[ngword]
extra_paths = []                    # 追加 NGワードファイルのパス列

[plugins]
enabled = ["shop", "chat"]          # 有効化されたプラグインの kind 一覧

[shop]                              # プラグインが追加するセクション
difficulty = "easy"
volume     = 80

[chat]
greeting = "こんにちは！"
```

### companion_core 側の読み込み

`companion_core.config` モジュールを新設し、`config.toml` を読み込む関数を追加する。  
パーサーは標準ライブラリの `tomllib`（Python 3.11+）を使い、**dependency-zero 原則を維持する**。

```python
# 優先順位: config.toml > 環境変数（後方互換）
from companion_core.config import load_config
cfg = load_config()   # デフォルト: ~/.streaming-companion/config.toml
client = make_client_from_config(cfg)
```

既存の `make_client_from_env` は維持（後方互換）。

---

## 設定変更の反映

設定UIは**独立プロセス**として起動する。設定を保存しても実行中の companion には即時反映されない。  
OK ボタン押下後に「変更を適用するには companion を再起動してください」を表示する。

---

## boundary ガード

`tests/test_boundary.py` の禁止リストに `companion_settings` を追加し、  
`companion_core` が `companion_settings` を import しないことを自動ガードする。

---

## 対応プラットフォーム

| OS | 対応 |
|---|---|
| Windows 10/11 | 必須 |
| macOS 12+ | 対応 |
| Linux | 非対象（PySide6 は動くが保証外） |
