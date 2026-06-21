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

    def build_workers(self, ingest, config) -> list[Worker]:
        # ingest を sink に注入して worker 群を組む (comment が console へ流れる)
        ...

    # synth(config) / player(config) は任意 override（通常は不要）
```

`config` は `companion_core.config.load_config()` の結果（dict）。provider は自分の
セクション（例 `[bpb]`）を読み、無ければ既定値を使う。

**TTS 合成 (synth) と再生 (player) は generic なので core が config から既定構築する**
（VOICEVOX = `[voicevox]` セクションの speaker/base_url、player = OS 既定デバイス）。ゲーム
タイトル単位で TTS を差し替える需要は稀なため、provider の責務は実質 `build_workers` のみ。
provider が `synth`/`player` メソッドを持つ場合だけ override される（薄い seam、BPB は使わない）。

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

`companion_core.console_providers.build_service(provider, config)` が組み立てを担い、
`companion_settings/__main__.py` の `main()` が呼ぶ:

```python
# companion_core/console_providers.py
def build_service(provider, config, ...):
    synth = provider.synth(config) if hasattr(provider, "synth") else _default_synth(config)
    player = provider.player(config) if hasattr(provider, "player") else _default_player(config)
    svc = ConsoleService(None, ConsoleState(), synth=synth, player=player)
    svc.supervisor = Supervisor(provider.build_workers(svc.ingest, config))  # 循環解消の順
    return svc

# companion_settings/__main__.py
def main():
    cfg = load_config()
    providers = discover_console_providers()
    svc = build_service(providers[0], cfg) if providers else None   # MVP: 先頭 provider
    app = QApplication(sys.argv)
    MainWindow(cfg=cfg, console_service=svc).show()                 # svc 有→「ライブ」タブ
    sys.exit(app.exec())
```

- **synth/player は core 既定**（`_default_synth` = `[voicevox]` から VoicevoxSink、`_default_player` = `make_player`）。provider override は任意。
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
  `companion_core.console_providers` に登録。**`build_workers` のみ**（synth/player は core 既定）。
  - `build_workers(ingest, cfg)` = 既存 `_build_workers` を再利用し `extra_sinks=[ingest]`。
    config は `cfg.get("bpb", {})` の値（save/rec/bundle/items_master/interval 等）＋既定値。
  - TTS の speaker は generic な `[voicevox].speaker`（ずんだもん = 3）で設定する。
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

## 追補 (v0.9.1): TTS 設定タブ

synth/player を core 既定構築にした以上、TTS 設定 (`[voicevox]`) も core が読む関心。GUI が
無いと config.toml 手編集になるため、**built-in の TTS 設定パネル**を統合 console に追加する
（TTS は generic なので BPB plugin ではなく built-in、LLM パネルと同じ作り）。

- `companion_settings/panels/voicevox.py` `VoicevoxPanel`: speaker / base_url。
- **反映モデル**: 編集 (commit) → 起動中 console に **live 反映**（`MainWindow._apply_voicevox` が
  `_default_synth({"voicevox": new})` で `ConsoleService.synth` を差し替え、再起動不要）。
  **保存** → config.toml `[voicevox]` を load-merge-save で永続化（他セクション保持）。
  **破棄** → 直近保存値にフィールドを戻し live も戻す。
- `console_service` が無い（設定のみ起動）なら apply は no-op、保存のみ効く。

## スコープ外（YAGNI）

- provider 固有のリッチ live ビュー（shop offers/round/gold 表示）。MVP は generic な now-speaking/history。
- 複数 provider の同時起動・選択 UI（MVP は先頭 provider）。
- provider 設定の専用 settings タブ（`companion_core.settings` 経由）。将来追加可。
- SpeechGate パラメータの無停止 live 反映（restart 経由のまま）。
