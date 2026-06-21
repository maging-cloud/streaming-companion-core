# Console 分離 + 3-repo 再編 設計仕様

**日付:** 2026-06-21
**対象:** streaming-companion-core / (新) streaming-companion-console / streaming-companion-bpb

---

## 概要

統合 PySide6 console を **公開・汎用のアプリ**として `companion_core` から分離する。

- `companion_settings` → **`companion_console`** に rename し、**新しい公開 repo** `streaming-companion-console` へ移設。
- **プラグインは同梱しない**: `companion_console` は plugin(provider / settings panel)を entry-point で
  **discover するだけ**で、特定 plugin に依存しない。将来の公開 plugin は同梱もありうるが、本設計では無し。
- **`companion_bpb` は非公開かつ UI ゼロ**: PySide6 を一切持たない。console 向けの設定パネルは
  **宣言的 (JSON Schema) パス**で定義する(純 dict、UI 非依存)。

依存(import)方向:
```
companion_core    (公開 lib, deps なし, UI なし)
   ▲                         ▲
companion_bpb              companion_console
(非公開 plugin,            (公開 UI アプリ,
 deps: core, UI なし)       deps: core + PySide6,
                            bpb には依存しない)
```
実行時の合成(矢印 core→bpb→console の意味): core を bpb plugin が使い、その plugin を console が
entry-point で discover して画面に出す。**import 依存ではない。**

---

## repo / package 構成

| repo | 公開 | package | 主な deps | 役割 |
|---|---|---|---|---|
| `streaming-companion-core`(既存) | 公開 | `companion_core` のみ | なし | 基盤 lib(console ロジック含む、UI なし) |
| `streaming-companion-console`(**新規**) | 公開 | `companion_console` | `streaming-companion-core` + PySide6 | 統合 PySide6 UI アプリ(`companion-console`) |
| `streaming-companion-bpb`(既存) | 非公開 | bpb plugin | `streaming-companion-core` | BPB plugin(provider + settings schema、**UI なし**) |

`companion_console` は core repo から撤去する(core は純 lib に戻す)。

---

## companion_core に残すもの / 移すもの

**core に残す(UI 非依存)**:
- `console/` (ConsoleState / ConsoleService / playback)
- `supervisor.py`
- `console_providers.py`(discover + build_service。`_default_synth`/`_default_player` 含む)
- `config.py`(load/save)
- `orchestrator.py`(SpeechGate)、sinks、llm、ngword、registry、handlers 等

**console repo へ移す(UI)**:
- `window.py`(MainWindow)、`live_panel.py`、`panels/`(llm/ngword/plugins/voicevox)、
  `schema_ui.py`、`registry.py`(settings panel discover)、`__main__.py`
- `companion-console` / `companion-settings` script、`ui` extra、PySide6 関連 CI/tests

> 注: settings 系の entry-point group 名(`companion_core.settings` / `companion_core.console_providers` /
> `companion_core.handlers`)は **互換のため変更しない**(plugin の登録先を壊さない)。discover の実装は
> console repo 側に移るが、group 名は core 名前空間のまま。

---

## companion_bpb: UI を持たずに console パネルを定義する

panel 契約は2系統(既存)。**bpb は宣言的(JSON Schema)パスを使う**:

```python
# commenter/console_settings.py  (UI import なし)
class BpbConsoleSettings:
    section_id = "bpb"
    label = "Backpack Battles"
    icon = "🎮"
    schema = {
        "type": "object",
        "properties": {
            "save":         {"type": "string", "title": "save path"},
            "rec":          {"type": "string", "title": "recommendation.json"},
            "bundle":       {"type": "string", "title": "scorer bundle"},
            "items_master": {"type": "string", "title": "items_master.json"},
            "interval":     {"type": "number", "title": "polling 間隔(秒)"},
            "min_interval": {"type": "number", "title": "最小発話間隔(秒)"},
            "score_delta":  {"type": "number", "title": "発話スコア閾値"},
            "save_watch":   {"type": "boolean", "title": "save-watch 有効"},
            "live":         {"type": "boolean", "title": "live 有効"},
            "battle":       {"type": "boolean", "title": "battle 有効"},
        },
    }
```
```toml
[project.entry-points."companion_core.settings"]
bpb = "commenter.console_settings:BpbConsoleSettings"
```

- `schema` は純 dict → **PySide6 を import しない**。Qt 化は console 側 `schema_ui.build_form` が担う。
- console の「BPB」設定タブで `[bpb]` を編集 → config.toml に保存 → bpb provider が `cfg["bpb"]` を読む。
- `console_providers`(build_workers)と `settings`(schema)は別 entry-point、どちらも bpb が UI なしで登録。

### schema_ui 拡張(console 側)

現 `schema_ui` は string/number/integer/enum 対応。`[bpb]` の bool 用に
**`boolean` → `QCheckBox`** を追加する(`get/set_values` も対応)。console repo で実装。

---

## 配信機での動かし方

1 つの venv に **`companion_console`(PySide6 + core)** と **非公開 `companion_bpb`** を両方インストール。
console が bpb の console_provider と settings panel を discover。PySide6 は console 側の依存なので
`uv sync` で prune されない。**bpb は UI を一切宣言しない**(PR #60 のような bpb[ui] は作らない)。

---

## 移行ステップ(cross-repo)

1. **PR #60 を close**(bpb[ui] は誤り)。bpb の `ui` extra と pin は別途整理。
2. **新規公開 repo `streaming-companion-console`** を作成(MIT)。CI(ui+offscreen+libegl1)/ release workflow を core から流用。
3. core repo の `companion_settings` を console repo へ移設し `companion_console` に rename。
   `schema_ui` に boolean 対応を追加。console は `streaming-companion-core` を依存(git pin)。
4. core repo から `companion_settings` を撤去、`ui` extra / console script を削除、純 lib 化、version bump。
5. bpb repo: `commenter/console_settings.py`(宣言的 schema パネル)を追加し `companion_core.settings` に登録。
   bpb の `ui` extra を撤去(UI ゼロ)。pin を新 core 版へ。
6. console repo: bpb plugin と一緒に動作確認(provider + settings タブ)。

> 公開 repo の作成・push は不可逆。review 結果を確認してから直列で。push 先 remote を確認する。

---

## 不変条件 / 境界

- `companion_core` は UI(PySide6)も `companion_console` も `companion_bpb` も import しない。
- `companion_console` は `companion_bpb` を import しない(plugin は entry-point discover)。
- `companion_bpb` は PySide6 を import しない(宣言的 schema のみ)。
- boundary test を各 repo に配置(core: settings/bpb を import しない / bpb: PySide6 を import しない)。

---

## スコープ外(YAGNI)

- 命令的(`build_widget`)パスでの bpb リッチ UI(PySide6 が要る → bpb UI ゼロに反する)。
- console が特定の公開 plugin を同梱すること(将来。本設計では console は plugin 非依存)。
- bpb repo の package 名を `companion_bpb` に統一する rename(現状 commenter/scorer のまま。任意・別途)。
- 複数 provider の選択 UI(MVP は先頭 provider)。
