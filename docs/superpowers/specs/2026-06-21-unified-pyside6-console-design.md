# Unified PySide6 Operator Console 設計仕様

**日付:** 2026-06-21
**対象:** streaming-companion-core（+ streaming-companion-bpb の plugin 化）

---

## 概要

operator console の web フロント（HTTP backend + 静的 UI）と設定 UI（PySide6）を、**単一の
PySide6 アプリ**に統合する。設定タブ（LLM/NGword/プラグイン）に「ライブ」タブ（start/stop/
mute/replay/now-speaking）を加え、1 つのウィンドウで配信中の制御と設定編集を行う。

BPB 固有の組み立て（worker 群・TTS）は **entry-point plugin** 化する。汎用 console が
`companion_core.console_providers` を discover して `ConsoleService` を組み立てるため、
`bpb-companion --console` は廃止し、汎用 `companion-console`（Qt）で起動する。

UI 非依存の制御ロジック（`ConsoleState`/`ConsoleService`/`Supervisor`/`playback`）は
`companion_core` に**そのまま残す**。Qt はそれを HTTP 無しで直接駆動する。

---

## アーキテクチャ

### 層と配置

```
companion_core/                      ← UI 非依存 (stdlib, dep ゼロ) — 変更最小
  console/state.py / service.py / playback.py   ← 既存のまま
  supervisor.py                                 ← 既存のまま
  console_providers.py  ← 新設: console provider の discover (entry-point)

companion_settings/                  ← PySide6 UI (統合 console)
  window.py             ← MainWindow に「ライブ」タブ (LivePanel) を追加
  live_panel.py         ← 新設: LivePanel (ConsoleService を駆動する Qt widget)
  __main__.py           ← provider を discover → ConsoleService 構築 → MainWindow 起動
  console/              ← 削除 (backend.py + static)
```

### 依存方向（不変条件）

- `companion_settings` は provider を **entry-point 文字列で discover**（BPB を import しない）。
- `companion_core` は `companion_settings` を import しない（boundary test 維持）。
- BPB の provider は `companion_core` を import 可（一方向）。

---

## console provider 契約

BPB が entry-point group **`companion_core.console_providers`** に登録するオブジェクト
（duck typing、settings panel と同流儀）:

```python
class ConsoleProvider:
    label: str                                   # 表示名 (任意)

    def synth(self, config) -> callable | None:  # callable(text) -> wav bytes。None 可 (TTS 無し)
        ...
    def player(self, config) -> callable | None: # callable(wav)。None 可 (再生無し)
        ...
    def build_workers(self, ingest, config) -> list[Worker]:
        # ingest を sink に注入して worker 群を組む (comment が console へ流れる)
        ...
```

`config` は `companion_core.config.load_config()` の結果（dict）。provider は自分の
セクション（例 `[bpb]`）を読み、無ければ既定値を使う。

### discover（companion_core/console_providers.py）

```python
def discover_console_providers() -> list:
    """companion_core.console_providers entry-point から provider を検索・instantiate。"""
    providers = []
    for ep in importlib.metadata.entry_points(group="companion_core.console_providers"):
        try:
            providers.append(ep.load()())
        except Exception:
            pass
    return providers
```

`companion_core.registry`/`companion_settings.registry` の既存パターンに倣う（失敗は握りつぶす）。

---

## 組み立て（汎用起動）

`companion_settings/__main__.py` の `main()`:

```python
def main():
    from PySide6.QtWidgets import QApplication
    from companion_core.console_providers import discover_console_providers
    from companion_core.console.state import ConsoleState
    from companion_core.console.service import ConsoleService
    from companion_core.supervisor import Supervisor
    from companion_core.config import load_config
    from companion_settings.window import MainWindow

    cfg = load_config()
    providers = discover_console_providers()
    svc = None
    if providers:
        p = providers[0]                                  # MVP: 先頭 provider を採用
        synth = p.synth(cfg) if hasattr(p, "synth") else None
        player = p.player(cfg) if hasattr(p, "player") else None
        state = ConsoleState()
        svc = ConsoleService(None, state, synth=synth, player=player)
        svc.supervisor = Supervisor(p.build_workers(svc.ingest, cfg))
        state.set_workers(svc.supervisor.status())

    app = QApplication(sys.argv)
    win = MainWindow(cfg=cfg, console_service=svc)         # svc 有→「ライブ」タブ表示
    win.show()
    sys.exit(app.exec())
```

- **循環の解消**: synth/player を先取得 → svc 生成 → `build_workers(svc.ingest, cfg)`。
- provider が無ければ `svc=None` で「ライブ」タブ無し（設定のみ）。core 単体でも起動可。
- `companion-console` と `companion-settings` は同じ `main()` を指す（統合ウィンドウ）。

---

## LivePanel（companion_settings/live_panel.py）

`ConsoleService` を駆動する Qt widget。`MainWindow` が `console_service` を持つときのみ
タブ追加。設定保存（`_on_ok`）とは独立（runtime action であって config 書き込みではない）。

- **ボタン**: START/STOP（トグル）・MUTE/UNMUTE・再生 → `svc.control("start"|"stop"|"mute"|"unmute"|"replay")`。
- **表示**: 状態バッジ（running）・NOW SPEAKING（`snapshot["current"]["text"]`）・history リスト・workers。
- **ライブ更新**: `svc.state.subscribe()`（`queue.Queue`）を **QThread で `q.get()` drain → Qt signal**
  で GUI スレッドへ転送し再描画（web の SSE と同じ流儀）。初期表示は `svc.get_state()`。
  ウィンドウ close 時に `state.unsubscribe(q)` + thread 停止。

`MainWindow.__init__(cfg=None, extra_panels=None, console_service=None)` を追加し、
`console_service` が真なら `self._tabs.addTab(LivePanel(console_service), "ライブ")`。

---

## BPB 側

- **`commenter/console_provider.py`（新設）**: `BpbConsoleProvider` を実装し
  `companion_core.console_providers` に登録。
  - `synth(cfg)` = `VoicevoxSink(speaker=<cfg or 3>).synthesize`
  - `player(cfg)` = `make_player()`
  - `build_workers(ingest, cfg)` = 既存 `_build_workers` を再利用し `extra_sinks=[ingest]`。
    config は `cfg.get("bpb", {})` の値（save/rec/bundle/items_master/interval 等）＋既定値。
- **`commenter/orchestrator.py`**: `_run_console` と `--console`/`--speaker`/`--host`/`--port` を**削除**。
  `bpb-companion`（通常の headless 並行起動）は不変。`_build_workers` は provider から呼ぶため残す。
- **`pyproject.toml`**:
  ```toml
  [project.entry-points."companion_core.console_providers"]
  bpb = "commenter.console_provider:BpbConsoleProvider"
  ```
  pin を新 core 版へ更新。

---

## 削除・後片付け（web console 撤去に伴う）

- `companion_settings/console/`（`backend.py` + `static/index.html`）を削除。
- `companion-console` script を Qt の `companion_settings.__main__:main` へ repoint（PySide6 必須）。
- `[project.optional-dependencies]` の **`console` extra を削除**（stdlib web 用だった）。`ui` extra に集約。
- `scripts/check_wheel.py` の静的アセット必須チェックを撤去（static 消滅）。build ジョブは残し
  「wheel build 成功 + clean env import」を検証（import 対象は `companion_settings.window`）。
- `tests/test_settings_console.py`（HTTP backend テスト）を削除。`tests/test_packaging.py` は
  「Qt app（`companion_settings.window`/`__main__`）が import 可能」検証に変更。
- CI `ci.yml` build ジョブの import チェックを `companion_settings.window` に更新。

---

## テスト方針

- **LivePanel / MainWindow**: `QT_QPA_PLATFORM=offscreen` で headless 構築テスト。
  ボタン click → `svc.control` 呼び出し、snapshot → ラベル反映を検証（`@skipUnless(HAS_PYSIDE6)`）。
  ライブ更新スレッドは注入可能にして決定的にテスト（QThread を使わず queue を直接流す経路を用意）。
- **console_providers discover**: fixture provider を entry-point 無しに直接渡せる形でロジック検証
  （既存 `companion_core/registry` テストの流儀）。
- **provider 組み立て**: synth/player 先取得 → svc → build_workers(ingest) の順を単体検証。
- **BPB provider**: `build_workers` が全 worker off で `[]`、extra_sinks に ingest が入ることを検証
  （既存 `test_orchestrator` の流儀）。
- boundary test: `companion_core` が `companion_settings` を import しないこと、`companion_settings`
  が BPB を import しないことを維持。

---

## 段階（cross-repo）

1. core: `console_providers.py` + `LivePanel` + `MainWindow` 拡張、web console 削除、pyproject/CI/tests 更新、version bump。PR → merge → tag（release workflow が wheel 自動添付）。
2. BPB: `console_provider.py` 登録 + `--console` 削除 + pin 更新。PR → merge。

> 公開 repo への push は不可逆。review 結果を確認してから直列で実行する。push 先 remote を確認する。

---

## スコープ外（YAGNI）

- provider 固有のリッチ live ビュー（shop offers/round/gold 表示）。MVP は generic な now-speaking/history。
- 複数 provider の同時起動・選択 UI（MVP は先頭 provider）。
- provider 設定の専用 settings タブ（`companion_core.settings` 経由）。将来追加可。
- SpeechGate パラメータの無停止 live 反映（restart 経由のまま）。
