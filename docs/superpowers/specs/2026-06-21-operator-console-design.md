# Operator Console 設計仕様

**日付:** 2026-06-21
**対象:** streaming-companion-core（一部 streaming-companion-bpb 側 refactor を伴う）

---

## 概要

配信中の運用者が使う **operator console**。実況パイプラインを GUI から live 制御する。
機能: **start/stop**・**現在の発話テキスト表示**・**mute**・**手動 replay**・**設定編集**。

core の純度制約（runtime 依存ゼロ・stdlib のみ）を守りつつ、**UI を後から差し替え可能**にする。
当初は web UI、最終的には Rust（Tauri / egui）ないし Python+Qt（PySide6）へ差し替えても backend を無改修で載せ替えられる構造にする。これを実現する durable な境界は **安定 API 契約** である。

本機能は BPB 固有ではなく **generic な streaming-companion 機構** なので `companion_core` に属する。
comment は `str`、sink は callable であり、console は handler/ゲームを一切 import しない。

> 既存 `companion_settings`（PySide6 の config.toml 静的エディタ。「再起動して反映」モデル）とは
> 「設定編集」のみ重複する。start/stop・発話表示・mute・replay は全て新規。
> 将来 `companion_settings` を本 console backend の Qt クライアントへ発展させる余地を残すが、本 spec の対象外。

---

## アーキテクチャ

### 3層構造（UI 差し替え可能性の核）

```
① Frontend（差し替え可能）
   今: web UI（HTML/JS, companion_core 同梱の静的アセット）
   後: Rust（Tauri/egui）/ Python+Qt（PySide6）— 同じ API を叩くだけ
        ▲▼  ── 安定 API 契約（durable な境界）──
            HTTP+JSON: GET /state ・ POST /control ・ GET·PUT /config
            SSE:       GET /events（comment / 状態 push）
② Console backend service（companion_core, generic, stdlib）
   Supervisor ・ ConsoleBackend ・ player ・ ConfigStore
        ▲▼  ── in-process（直接呼び出し）──
③ workers（BPB が entrypoint で組み立て注入）
   save-watch → recommend(handler) → comment(str) → sinks
```

### 採用方針: in-process host

backend は workers を **同一プロセスで host** する（subprocess ではない）。
利点: live 状態（現在 comment / round / worker health）へ直接アクセスでき status file 不要、
mute/replay/TTS が backend 内で完結しプロセス間調整が無い。

### 境界の維持

`companion_core`（console/supervisor 含む）は **BPB を import しない**。
generic な部品は core に置き、**BPB は自分の entrypoint で core の部品を組み立て、workers を注入**する
（handler の entry-point と同じ発想）。依存方向は従来通り **BPB → companion_core の一方向**。

---

## パッケージ / コンポーネント構成

```
src/companion_core/
  supervisor.py   ← 新設: generic worker lifecycle（BPB から lift・generalize）
  console/        ← 新設
    __init__.py
    backend.py    ← ConsoleBackend: ThreadingHTTPServer, API, 静的UI配信
    state.py      ← ConsoleState: 現在 comment / history / worker 状態 / muted
    playback.py   ← player: platform 分岐の WAV 再生（winsound/afplay/aplay）
    static/        ← web UI（index.html / app.js / style.css）
  config.py       ← 既存を拡張（[console] [speech] [playback] [voicevox] 追記。save 統合）
  orchestrator.py ← 既存 SpeechGate（変更なし）
  sinks/voicevox.py ← 既存（player 注入口は既にある。変更最小）
```

### コンポーネント責務

| 部品 | 責務 | 依存 |
|---|---|---|
| `Supervisor` | 注入された worker callable 群を thread で start/stop/health。協調停止フラグを各 worker に渡す | stdlib (threading) |
| `ConsoleState` | live 状態の単一の持ち主（現在 comment, history[], round/meta, muted, running, worker 健康度） | なし |
| `ConsoleBackend` | `ThreadingHTTPServer`。API ルーティング・SSE 配信・静的 UI 配信。Supervisor / ConsoleState / player / config を結線 | stdlib (http.server) |
| `player` | WAV bytes を OS 既定デバイスへ再生。Windows=`winsound`, macOS=`afplay`, Linux=`aplay`（subprocess） | stdlib |
| `ConfigStore` | `config.toml` の load/save（既存 `config.py` を拡張・統合） | stdlib (tomllib) + `tomli-w`（save のみ） |

### TTS・再生の所有

backend が **TTS 合成と再生を一元所有**する。
live worker の comment は in-process sink で `ConsoleState` へ渡り、backend が
`VoicevoxSink`（合成）→ `player`（再生）を駆動する。
- **mute** = backend が再生を行わない（合成はしてもよい/省いてもよい。MVP は再生スキップ）。
- **replay** = 直近の WAV を player で再生し直す（`ConsoleState` が last_wav を保持）。

> SpeechGate（発話 gating）は worker 側に残す。console は gating 済みの発話を受けて喋る。
> `[speech]` の min_interval / score_delta は config 経由。live 反映は **stop→config保存→start**（backend が clean に再起動）で行う（MVP）。

---

## API 契約（最重要・後方互換を維持）

transport は HTTP+JSON（コマンド/状態）+ SSE（push）。Rust / Qt から自明に消費可能。

### `GET /state` → 200 JSON
```json
{
  "running": true,
  "muted": false,
  "workers": [{"name": "save-watch", "alive": true}, {"name": "live", "alive": true}],
  "current": {"text": "今回は Leather Bag を確保するのだ。", "ts": 1781999999.0, "meta": {"round": 7, "gold": 42}},
  "history": [{"text": "Reroll してもいいのだ…", "ts": 1781999990.0}]
}
```
`meta` は handler 非依存の任意 dict（BPB が round/gold を載せる。console は素通し表示）。

### `POST /control` → 200 JSON `{"ok": true, "state": {...}}`
body: `{"action": "start" | "stop" | "mute" | "unmute" | "replay"}`

### `GET /config` → 200 JSON / `PUT /config` → 200 JSON
`config.toml` を JSON 化して返す / セクション単位で受けて保存。
（再起動が要る変更は `{"restart_required": true}` を返す。）

### `GET /events` → `text/event-stream`（SSE）
`ConsoleState` の変化（新規 comment / worker 状態 / muted / running）を逐次 push。
イベント形式: `event: state\ndata: </state と同形の JSON>\n\n`。

### `GET /` ほか静的パス
`console/static/` の web UI を配信（index.html / app.js / style.css）。

**規律:** ロジックを JS に書かない（薄い表示のみ）。realtime 再生・timing 等の制御は必ず backend 側。

---

## Worker lifecycle（core への lift）

現状、worker 機構（`Worker` / `worker_loop` / `run_workers`）は **BPB 側 `commenter/orchestrator.py`** にのみ存在し、core には generic 抽象が無い。これを core へ持ち上げる。

### `companion_core.supervisor`（新設）

```python
class Worker:
    name: str
    tick: Callable[[], None]      # 1 回分の処理（例: save をポーリングして発話）
    interval: float

class Supervisor:
    def __init__(self, workers: list[Worker], spawn=None, clock=None): ...
    def start(self) -> None: ...      # 各 worker を thread 起動
    def stop(self) -> None: ...       # 協調停止フラグを立てて join
    def status(self) -> list[dict]: ...  # [{"name","alive"}]
```

- 各 worker thread は **協調停止フラグ**（`threading.Event`）を監視し、tick 境界で抜ける（Python の thread は clean kill 不可のため）。
- `spawn` / `clock` は注入可能にしてテストを headless 化（既存 SpeechGate と同じ作法）。

### BPB 側の再ターゲット（cross-repo）

`commenter/orchestrator.py` は自前の worker 機構を捨て、`companion_core.supervisor` を消費する。
tick の中身（save-watch / recommend(handler) / battle）の wiring は BPB に残る。
新 entrypoint（例 `bpb-companion --console`）が「workers 組み立て → `Supervisor` 構築 → `ConsoleBackend` 起動」を行う。

---

## Realtime playback（デバイス選択方針）

| 段階 | 方式 | 依存 |
|---|---|---|
| **MVP** | OS 既定デバイス経由。VB-CABLE 等を OS 既定にして `player` が即再生。これで「リアルタイム自動再生」を満たす（OBS 不要） | stdlib のみ |
| 後日 | アプリ内デバイス選択（出力先を UI で指定） | `sounddevice` 等を **別 optional extra** として追加。core 純度を保つため後回し |

`player` は platform 分岐:
- Windows: `winsound.PlaySound(wav_path, SND_FILENAME|SND_ASYNC)`
- macOS: `subprocess` で `afplay`
- Linux: `subprocess` で `aplay`

（`winsound`/`afplay`/`aplay` はデバイス選択不可。MVP は OS 既定にルーティングする前提。）

---

## 設定ファイル拡張

`~/.streaming-companion/config.toml` に追記（既存 `[llm] [ngword] [plugins]` はそのまま）:

```toml
[console]
host = "127.0.0.1"
port = 8765

[speech]
min_interval = 5.0
score_delta  = 0.1

[playback]
enabled = true
# device = "..."   # 後日（in-app device selection）

[voicevox]
speaker  = 3                       # ずんだもん ノーマル
base_url = "http://localhost:50021"
```

- `config.py` を拡張し save も提供（現状 save は `companion_settings/config.py` に重複。これを `companion_core.config` に統合し、`companion_settings` は core を呼ぶ）。
- save に要る `tomli-w` は新 optional extra `console = ["tomli-w>=1.0"]`（web UI 自体は依存ゼロ）。

---

## Web UI（layout A）

「ライブ優先」レイアウト。配信中のグランス用途。

```
┌──────────────────────────────────────────────┐
│ ● RUNNING  R7/42g      [⏹STOP][🔇MUTE][🔁再生] │ ← 制御バー
├──────────────────────────────────────────────┤
│ NOW SPEAKING                                  │
│ 「今回は Leather Bag を確保するのだ。」          │ ← 発話フィード（SSE で更新）
│ ── history ──                                 │
│ R6「Reroll してもいいのだ…」                    │
├──────────────────────────────────────────────┤
│ ▸ 設定（speaker/sinks/device/timing/LLM）折りたたみ │
└──────────────────────────────────────────────┘
```

- `/events`(SSE) を購読し NOW / history / 状態バッジを更新。
- 制御は `POST /control`、設定は `GET·PUT /config`。
- 静的アセットのみ（ビルド工程なし、依存ゼロ）。OBS browser source にも流用可能。

---

## 新 console-script / インストール

```toml
[project.optional-dependencies]
console = ["tomli-w>=1.0"]          # web UI は依存ゼロ。save に tomli-w のみ

[project.scripts]
companion-console = "companion_core.console.backend:main"   # core 単体起動（workers 無し）
```

BPB 側は entrypoint（`bpb-companion --console`）で workers を注入して起動する。

---

## boundary ガード / テスト

- `tests/test_boundary.py`: `companion_core` が `companion_settings` / BPB を import しないことを引き続きガード。新 `console` パッケージも core 純度（stdlib + optional `tomli-w` のみ）を満たすことを確認。
- テスト規約は既存に倣う（flat `tests/`, `unittest`, optional-dep は `@skipUnless` ガード, headless 注入）。
  - `Supervisor`: `spawn`/`clock` 注入で thread を使わず tick 駆動を検証。
  - `ConsoleBackend`: `http.client` で各 API を叩いて検証（ブラウザ不要）。
  - `player`: subprocess/winsound 呼び出しを注入で差し替えて検証。

---

## cross-repo 段取り（公開 push を伴う）

1. core に Supervisor / console / playback / config 拡張を実装、テスト green。
2. core の **version bump（v0.8.0）** + tag、公開 repo へ push。
3. BPB 側 `commenter/orchestrator.py` を core supervisor 消費へ refactor、`--console` entrypoint 追加。
4. BPB の `pyproject.toml` の git pin を v0.8.0 に更新。

> 公開 repo への push は不可逆。review 結果を確認してから直列で実行する。
> push 直前に送信先 remote URL（`maging-cloud/streaming-companion-core`）を確認する。

---

## 対応プラットフォーム

| OS | 対応 | 備考 |
|---|---|---|
| Windows 10/11 | 必須 | `winsound` 再生。VB-CABLE を OS 既定に |
| macOS 12+ | 対応 | `afplay` 再生（開発機） |
| Linux | best-effort | `aplay`（PySide6 同様、保証外） |

---

## スコープ外（YAGNI）

- アプリ内オーディオデバイス選択（optional dep 必要 → 後日）。
- handler view hook（shop offers 等の構造化表示）。MVP は generic な comment テキスト表示のみ。
- Rust / Qt フロントエンド実装そのもの（本 spec は backend と web UI のみ。API 契約で後続を可能にする）。
- SpeechGate パラメータの無停止 live 反映（MVP は restart 経由）。
- `companion_settings` の console クライアント化。
```
