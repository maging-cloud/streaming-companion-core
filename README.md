# streaming-companion-core (`companion_core`)

配信実況コンパニオンの汎用基盤 (ゲーム非依存)。構造化入力 (推薦/イベント等) → 安全な実況文を生成する。
ゲーム固有知識は持たず、**handler 注入 / entry-point plugin** で各ゲーム・ペルソナを差し込む。

## インストール
```
uv pip install -e .              # 開発
# または git 依存として:
# streaming-companion-core = { git = "https://github.com/maging-cloud/streaming-companion-core.git", tag = "v0.1.0" }
```

## モジュール (`companion_core`)
- request.py: CommentRequest{kind,payload} 規約 + make_request。
- registry.py: kind → handler 登録 + entry-point discovery (group `companion_core.handlers`)。
- prompt.py: build_prompt(request, handler) — handler.persona/fewshot/build_user から (system,user)。
- processor.py: sanitize + make_ng_filter + run_pipeline。
- phrasebook.py: pick(seed, options) — 決定的フレーズ選択 (テンプレ単調化を防ぐ、同一局面→同一文)。
- ngword.py: NGワード管理 (load_ngwords/contains_ng/default_paths)、`--list`。seed は同梱 ngwords.txt。
- sink.py: 出力 Sink (text 既定) + fan_out。
- sinks/file.py: file_sink(path) — 実況文を file へ書く Sink (OBS テキストソース用)。
- sinks/voicevox.py: VoicevoxSink — VOICEVOX HTTP で text→音声 (WAV)。HTTP は stdlib、再生は player 注入で依存ゼロ。
- comment.py: comment(request, handler, client, processors, ngwords) — NG を末尾常時付与する安全ゲート。
- orchestrator.py: SpeechGate — 発話タイミング制御 (スコア変動 + クールダウン + 重要イベント)。
- supervisor.py: Worker/worker_loop/Supervisor — 汎用 worker lifecycle (tick を thread で並行起動、協調停止)。
- console/: Operator Console の UI 非依存ロジック — ConsoleState (live 状態+SSE) / ConsoleService (制御+TTS所有) / playback (WAV 再生)。web フロント (HTTP backend+UI) は companion_settings 側 (下記)。
- chat_handler.py: ChatHandler (汎用基底, persona 注入式) + ZundamonChatHandler (既定 persona ずんだもん, ゲーム非依存)。
- sources/chat.py: from_chat (chat→CommentRequest) + ChatRouter (kind 振り分け) + keyword_matcher。
- sources/twitch.py: Twitch IRC parse + TwitchChatSource (PING 自動 PONG)。実接続 open_twitch_irc は network 依存。
- llm.py: OpenAI 互換 client (env COMPANION_LLM_BASE_URL/API_KEY/MODEL、旧 BPB_LLM_* も fallback 可)。

設計の詳細・データフロー・plugin の作り方は [ARCHITECTURE.md](ARCHITECTURE.md) を参照。

## Operator Console

配信中の live 制御 (start/stop/mute/replay/設定編集) を行う web console。実況パイプラインを
GUI から操作する。TTS 合成・再生は `ConsoleService` が所有し、worker は `Supervisor` で host する。

**層の分離**: UI 非依存の制御ロジック (`ConsoleService`/`ConsoleState`/`Supervisor`/playback) は
`companion_core` に、web フロント (HTTP backend + 静的 UI) は `companion_settings.console` にある。
設定 UI (PySide6) と同じ UI 層パッケージに同居する。web console 自体は stdlib のみで動き
PySide6 は不要 (`[console]` extra = tomli-w のみ)。

```
uv pip install -e ".[console]"
companion-console            # http://127.0.0.1:8765 (companion_settings.console.backend:main)
```

安定 API (`GET /state` · `POST /control` · `GET·PUT /config` · `GET /events` SSE) を持ち、
UI はその薄いクライアント。web UI を後から Rust/Qt フロントへ差し替えても、あるいは Qt フロントが
`ConsoleService` を直接駆動しても、UI 非依存ロジックは無改修。
音声再生は OS 既定デバイス経由 (stdlib: winsound/afplay/aplay)。VB-CABLE 等を既定にすると配信へ流せる。
`companion-console` 単体は workers 無しで UI/設定編集の確認用。実 worker 注入は consumer (BPB 等) の
entrypoint が `Supervisor` + `ConsoleService` を組み立てて行う。

設計: [docs/superpowers/specs/2026-06-21-operator-console-design.md](docs/superpowers/specs/2026-06-21-operator-console-design.md)

## plugin 規約 (handler, duck typing)
persona: str / fewshot: str (空可) / build_user(payload) -> str / template(request) -> str

外部パッケージは entry-point で handler を登録できる:
```
[project.entry-points."companion_core.handlers"]
shop = "yourpkg.handler:YourHandler"
```
`registry.get_handler("shop")` が遅延 discover する。本パッケージは plugin を import しない (一方向依存)。

## テスト
```
uv pip install -e .
python -m unittest discover -s tests -p "test_*.py"
```

## License
MIT
